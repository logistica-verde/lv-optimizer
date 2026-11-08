"""Compara o modelo MEET do código com um cálculo de referência feito fora do código.

A referência é a planilha docs/meet-referencia.xlsx, montada à mão a partir do relatório de
Hickman et al. (1999), TRL SE/491/98, Anexo A, sem copiar nada do código. A aba "casos" tem uma
linha por trecho, com as entradas e a emissão em gramas calculada na planilha. Enquanto a planilha
não existir ou estiver sem a emissão de algum caso, o teste é pulado.

Se algum caso não bater dentro de 0,1%, não ajuste o teste: a mensagem mostra a diferença em cada
fator (A10, A11 e A13/A14), para encontrar onde ela nasce.
"""

import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest

from app.optimization.meet_emission_model import MeetEmissionModel

SPREADSHEET = Path(__file__).resolve().parent.parent / "docs" / "meet-referencia.xlsx"
TOLERANCE = 0.001
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"

SOURCES = {
    "plano-vazio": "A10 (Tabela A24) x A11 = 1 em 0% x A13 sem carga = 1",
    "subida-2-vazio": "A10 (Tabela A24) x A11 para 0 a 4% (Tabela A37) x A13 sem carga = 1",
    "descida-2-vazio": "A10 (Tabela A24) x A11 para -4 a 0% (Tabela A37) x A13 sem carga = 1",
    "plano-carregado": "A10 (Tabela A24) x A11 = 1 em 0% x A14 com carga total (Tabela A43)",
    "subida-2-carregado": "A10 (Tabela A24) x A11 para 0 a 4% (Tabela A37) x A14 (Tabela A43)",
    "descida-2-carregado": "A10 (Tabela A24) x A11 para -4 a 0% (Tabela A37) x A14 (Tabela A43)",
    "rota-trecho-1": "A12 = A10 x A11 x A13 x distância, trecho 1 da rota curta",
    "rota-trecho-2": "A12 = A10 x A11 x A13 x distância, trecho 2 da rota curta",
    "rota-trecho-3": "A12 = A10 x A11 x A13 x distância, trecho 3 da rota curta",
}

COLUMNS = ("caso", "massa_kg", "carga", "velocidade_kmh", "declividade_percent", "distancia_km", "emissao_g")


def column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    index = 0
    for ch in letters:
        index = index * 26 + ord(ch.upper()) - ord("A") + 1
    return index - 1


def read_sheet(path: Path, sheet_name: str) -> list[list[str | None]]:
    with zipfile.ZipFile(path) as book:
        shared = []
        if "xl/sharedStrings.xml" in book.namelist():
            for item in ElementTree.fromstring(book.read("xl/sharedStrings.xml")).findall("m:si", NS):
                shared.append("".join(t.text or "" for t in item.iter(f"{{{NS['m']}}}t")))
        workbook = ElementTree.fromstring(book.read("xl/workbook.xml"))
        rels = ElementTree.fromstring(book.read("xl/_rels/workbook.xml.rels"))
        targets = {rel.get("Id"): rel.get("Target") for rel in rels}
        sheet = next(s for s in workbook.find("m:sheets", NS) if s.get("name") == sheet_name)
        target = targets[sheet.get(REL)].lstrip("/")
        root = ElementTree.fromstring(book.read(target if target.startswith("xl/") else f"xl/{target}"))
    rows = []
    for row in root.iter(f"{{{NS['m']}}}row"):
        values: list[str | None] = []
        for cell in row.findall("m:c", NS):
            position = column_index(cell.get("r"))
            values.extend([None] * (position - len(values)))
            raw = cell.find("m:v", NS)
            inline = cell.find("m:is/m:t", NS)
            if cell.get("t") == "s" and raw is not None:
                values.append(shared[int(raw.text)])
            elif inline is not None:
                values.append(inline.text)
            else:
                values.append(raw.text if raw is not None else None)
        rows.append(values)
    return rows


def reference_cases() -> list[dict]:
    if not SPREADSHEET.exists():
        pytest.skip("docs/meet-referencia.xlsx ainda não foi anexada (item A4)")
    rows = read_sheet(SPREADSHEET, "casos")
    header = [str(value).strip() if value else "" for value in rows[0]]
    position = {name: header.index(name) for name in COLUMNS}
    cases = []
    for row in rows[1:]:
        row = row + [None] * (len(header) - len(row))
        if not row[position["caso"]] or row[position["caso"]] == "rota-total":
            continue
        cases.append({name: row[position[name]] for name in COLUMNS})
    if any(case["emissao_g"] in (None, "") for case in cases):
        pytest.skip("a planilha ainda não tem a emissão calculada de todos os casos (item A4)")
    return cases


def test_the_reference_covers_every_case_the_tcc_cites():
    assert {case["caso"] for case in reference_cases()} == set(SOURCES)


@pytest.mark.parametrize("case_name", list(SOURCES))
def test_the_model_matches_the_hand_calculation(case_name):
    case = next(case for case in reference_cases() if case["caso"] == case_name)
    model = MeetEmissionModel(float(case["massa_kg"]), load_ratio=float(case["carga"]))
    v, slope, distance = float(case["velocidade_kmh"]), float(case["declividade_percent"]), float(case["distancia_km"])
    expected = float(case["emissao_g"])

    computed = float(model.calculate_emission(v, slope, distance))

    assert computed == pytest.approx(expected, rel=TOLERANCE), (
        f"{case_name} ({SOURCES[case_name]}): código {computed:.4f} g, planilha {expected:.4f} g. "
        f"Fatores do código: A10 {float(model.base_emission_g_per_km(v)):.4f} g/km, "
        f"A11 {float(model.gradient_factor(v, slope)):.6f}, A13 {float(model.load_factor(v, slope)):.6f}, "
        f"distância {distance} km"
    )


def test_the_short_route_is_the_sum_of_its_legs():
    legs = [case for case in reference_cases() if case["caso"].startswith("rota-trecho-")]
    model = MeetEmissionModel(float(legs[0]["massa_kg"]), load_ratio=float(legs[0]["carga"]))

    route = sum(
        float(model.calculate_emission(float(leg["velocidade_kmh"]), float(leg["declividade_percent"]),
                                       float(leg["distancia_km"])))
        for leg in legs
    )

    assert route == pytest.approx(sum(float(leg["emissao_g"]) for leg in legs), rel=TOLERANCE)
