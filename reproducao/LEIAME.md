# Pacote de reprodução do experimento do TCC

Leva alguém do zero aos mesmos números das Tabelas 1 e 2 do TCC (configuração padrão) e da análise de sensibilidade com 2.000 gerações. Montado em 2026-11-07.

## O que o experimento usa (e o que não usa)

O experimento principal roda sobre **instâncias sintéticas**:
- **Pontos:** são sorteados no centro de São Paulo; o ponto 0 é o depósito.
- **Distância:** é em linha reta (haversine) entre os pontos.
- **Velocidade e elevação:** cada par de pontos tem uma velocidade e cada ponto uma elevação, todas sorteadas.
- **Gerador:** cada instância usa o `numpy.random.default_rng(semente)` com semente igual ao número de pontos.

Ele **não** usa OpenStreetMap, OSRM nem SRTM, e por isso não depende de nenhum arquivo externo: o código e as sementes bastam. Os dados de mapa e de relevo só entram no sistema completo e no experimento de validação em ruas reais (`experiments/run_real_experiment.py`); a seção "Ambiente do sistema" registra a origem deles.

## Instâncias

`instancias/sintetica-NN.json` (n = 10, 15, 20, 25 e 30), gerados por `python -m reproducao.exportar_instancias`. Cada arquivo traz:
- **`points`:** latitude, longitude e elevação de cada ponto; o índice 0 é o depósito.
- **`generation`:** como os pontos foram sorteados (faixas, ordem dos sorteios, regra de distância e de declividade).
- **`segments`:** os n(n−1) trechos no formato do `POST /optimize`, que também é o formato de `--instances-dir`.
- **`speed_matrix_kmh`:** a matriz de velocidades sorteadas.

A fonte da verdade é a função `synthetic_instance`. Os arquivos servem para conferência; ao serem relidos, a conversão de metros para quilômetros pode mudar o último bit de alguma distância.

## Sementes

| O quê | Semente |
|---|---|
| Instância de n pontos | n |
| AG, repetições 1 a 3 | 1, 2 e 3 (a mesma nos dois critérios) |
| Linha de base aleatória | `default_rng([7919, semente do AG])`, separada do AG |

## Versões

| Item | Versão |
|---|---|
| lv-optimizer | `c008c72` (main de 2026-11-07); a rodada padrão está no PR da A5 |
| lv-api | `b729226` (main de 2026-11-07) |
| lv-frontend | `e9a653b` (main de 2026-11-07) |
| Python | 3.10.11 (Windows) ou 3.11.18 (contêiner do otimizador) |
| Bibliotecas | `requirements.txt`: numpy 1.26.4, fastapi 0.104.1, pydantic 2.5.0, pytest 7.4.3 |

## Como repetir

```bash
git clone https://github.com/logistica-verde/lv-optimizer && cd lv-optimizer
git checkout c008c72
python -m pip install -r requirements.txt

# configuração padrão do sistema (Tabelas 1 e 2): população 300, 500 gerações
python -m experiments.run_experiment --output-dir nova-padrao

# análise de sensibilidade: 2.000 gerações
python -m experiments.run_experiment --output-dir nova-2000 --population 300 --generations 2000 --crossover 0.9 --mutation 0.4

# comparação com as rodadas registradas
python reproducao/comparar.py experiments/resultados-padrao-2026-11-07/execucoes.csv nova-padrao/execucoes.csv
python reproducao/comparar.py experiments/resultados/execucoes.csv nova-2000/execucoes.csv
```

O que esperar:
- Configuração padrão: 15 de 15 execuções idênticas; 3 de 5 instâncias com Δ ≥ 5%; Δ médio de 8,92%.
- 2.000 gerações: 12 de 15 idênticas em todas as colunas. As outras 3 (`sintetica-10`) diferem só no 16º algarismo da distância (8,992156548841422 contra 8,992156548841423 km), por arredondamento na ordem da soma. Resultado: 4 de 5 instâncias com Δ ≥ 5%.
- Cada rodada leva cerca de 6 minutos (padrão) ou 25 minutos (2.000 gerações) num computador como o descrito abaixo.

## Rodadas registradas

| Pasta | Configuração | Onde rodou | Tempo por execução |
|---|---|---|---|
| `experiments/resultados-padrao-2026-11-07/` | padrão (300 × 500), com linha de base | i7-10700F, Windows | 11,6 a 12,9 s |
| `experiments/resultados/` | 2.000 gerações, 18/10/2026 | computador do André | 11,2 a 12,6 s |
| `experiments/resultados-reproducao-2026-11-01/` | 2.000 gerações, com linha de base | i7-10700F, Windows | 43 a 46 s |

Cada pasta tem `execucoes.csv` (sem arredondamento), `execucoes.json` (com sequências e curvas de convergência) e `resumo.json`; as mais recentes têm um `LEIAME.md`. O tempo depende da máquina, mas o resultado não: veja a explicação no `LEIAME.md` da rodada padrão.

## Hardware de referência

Intel Core i7-10700F (8 núcleos, 16 threads, 2,9 GHz), 15,9 GB de RAM, Windows 11 Pro 26200. O Docker Desktop reserva 4 CPUs e 6,2 GB para os contêineres. O script do experimento usa um único processo.

## Ambiente do sistema (fora do experimento principal)

Usado pela API, pela interface e pelo experimento em ruas reais.

| Item | Origem e versão |
|---|---|
| Mapa (OSRM) | recorte da Geofabrik `south-america/brazil/sudeste-latest.osm.pbf`, baixado em 18/10/2026; objetos até 2026-10-17 19:58 UTC; recortado com `osmium extract -b -46.95,-24.10,-46.25,-23.25` (`deploy/scripts/prepare-osrm.sh` do lv-api). `region.osm.pbf` com SHA-256 `1db2847912e2e2a945fe849e106a084ebe9dba4a17f9c8d1445e3744bbdf5ffa` |
| OSRM | `ghcr.io/project-osrm/osrm-backend@sha256:55dbfd47d984c2cacd64e32901b4321c86b5ec761438e69aa053dc78698a786f` (osrm-routed v26.10.0), perfil `/opt/car.lua` da imagem (SHA-256 `57778a757711e2ebef95d304e03e6ddf1a5693110d13a151914642344d59fa66`), algoritmo MLD |
| Relevo | SRTMGL1 (30 m), bloco `S24W047`, de `https://step.esa.int/auxdata/dem/SRTMGL1` (`deploy/scripts/prepare-srtm.sh`); `S24W047.hgt` com SHA-256 `f709cc0830c6fe34feccf412d3e95076616f793d67f82c90a05fad53caf9503b` |
| Besu | 26.10.0 no ambiente local (`hyperledger/besu@sha256:7ce78163f9de6733bb868c8bd2ebb4e6e90cc7cb950034ff8c333b1a0c27aace`); o compose passa a fixar 26.11.0 (lv-api, A3) |
| SQL Server | `mcr.microsoft.com/mssql/server@sha256:cf8f0ab2ebe61feec2eed2629061a07d247f791c2a8ddda74a4ac9f06a291718` (2022) |

Os arquivos de mapa e de relevo não estão neste repositório (141 MB e 26 MB). Os scripts do `deploy/` do lv-api baixam os mesmos, e os SHA-256 acima conferem a versão. A Geofabrik atualiza o "latest" diariamente; para o mesmo recorte, guardem o `region.osm.pbf` junto do pacote entregue à banca.
