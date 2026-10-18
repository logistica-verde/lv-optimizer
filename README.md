# lv-optimizer

Microsservico de otimizacao do sistema de Logistica Verde. Servico independente, executado em processo separado, cuja unica atribuicao e receber os trechos de via e devolver a melhor sequencia de entregas calculada por Algoritmos Geneticos.

Modulo do TCC *Sistema de Logistica Verde Inteligente com Otimizacao por Inteligencia Artificial e Auditoria em Blockchain* - Engenharia de Software, UNIP, 2026.

## O que resolve

Implementa o Green Vehicle Routing Problem na formulacao Pollution Routing Problem. A funcao de aptidao usa o modelo MEET, no qual a emissao de CO2 e funcao da velocidade media, da massa bruta do veiculo e da inclinacao do trecho.

O servico expoe os dois criterios de otimizacao que o experimento compara: menor distancia e menor emissao.

## Algoritmo

| Componente | Escolha |
|---|---|
| Representacao | Cromossomo de permutacao |
| Cruzamento | Order Crossover (OX) |
| Mutacao | Inversao de subsequencia |
| Avaliacao | Vetorizada com NumPy |

## Parametros do algoritmo genetico

`POST /optimize` aceita `ga_params` com `population_size`, `generations`, `crossover_rate` e `mutation_rate`. Campos omitidos usam os valores calibrados nas instancias sinteticas (populacao 300, 2000 geracoes, cruzamento 0,9, mutacao 0,4). O limite de tempo de 55 s continua valendo.

## Stack

- Python 3.11
- FastAPI
- NumPy

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Documentacao interativa da API em `http://localhost:8000/docs`.

## Docker

```bash
docker build -t lv-optimizer .
docker run --rm -p 8000:8000 lv-optimizer
```

A imagem usa Python 3.11, roda sem privilegios e responde `GET /health` no healthcheck. O compose completo do sistema esta no `lv-api` (pasta `deploy`).

## Contrato

O OpenAPI gerado pelo FastAPI e versionado em `contracts/optimizer-v1.json`. A `lv-api` consome essa interface, entao qualquer mudanca no formato de entrada ou saida deve ser tratada como decisao consciente e refletida no arquivo.

## Modulos do projeto

`lv-frontend` interface web - `lv-api` API REST - `lv-optimizer` este repositorio - `lv-infra` ambiente Docker - `lv-docs` documentacao
