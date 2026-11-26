# Pacote de reprodução dos ensaios em ruas reais (item L02)

Os 54 ensaios da validação em ruas reais foram executados em 2026-10-19, de 00:00 a 00:26 UTC, com `experiments/run_real_experiment.py` contra o sistema completo no Docker local: API, OSRM com o recorte do OpenStreetMap, SRTM, modelo MEET e AG. O resultado agregado está em `experiments/resultados-reais/`. Este pacote guarda o que faltava para repetir cada ensaio sem a API, o OSRM ou o SRTM: os pontos, os sorteios, as sementes e as matrizes de cada par de pontos.

## Conteúdo

| Arquivo | O que é |
|---|---|
| `pontos.json` | Os 21 pontos usados: as 15 entregas cadastradas (ids 1 a 15) e os 6 pontos de saída que a API criou a partir das coordenadas de cada origem (ids 16 a 20 e 22) |
| `ensaios.json` | Os 54 ensaios. Para cada um: origem, tamanho, pontos sorteados (na ordem do sorteio), pontos na ordem enviada ao otimizador, semente do AG, operações no banco, rota gravada de cada critério e os valores do `execucoes.csv` |
| `pares.json` | A matriz de todos os 420 pares ordenados entre os 21 pontos: distância e duração da rota no OSRM, velocidade média e declividade |
| `por-origem-e-tamanho.csv` | Os ensaios separados por origem e por tamanho |
| `matrizes_ruas_reais.py` | Recalcula `pares.json` a partir do OSRM e do serviço de elevação, com as mesmas regras da API |
| `reproduzir.py` | Roda o AG de novo em cada ensaio, a partir deste pacote, e compara com as rotas gravadas |

## De onde vem cada parte, e como foi conferida

- **Sorteios:** o script sorteia com `random.Random(2026)`, em ordem: origem, tamanho e três subconjuntos, com `sample` sobre os ids 1 a 15. Refeitos com a mesma semente, os 54 sorteios coincidem com os pontos das operações gravadas no banco.
- **Operações:** cada ensaio gerou duas operações (menor distância e menor emissão). As 108 foram identificadas no banco local (ids 74 a 185) pela emissão e pela distância de cada rota, que batem com o `execucoes.csv`.
- **Matrizes:** o banco só guarda os trechos da rota escolhida, então a matriz completa foi recalculada em 2026-11-26 por `matrizes_ruas_reais.py`. O script repete o caminho da API: `RoadNetworkSegmentSource`, `SlopeCalculator`, `OsrmClient`, `ElevationClient` e `GeoPoint.snapped`, sem alteração desde 2026-10-18. Ele consulta o mesmo OSRM e o mesmo SRTM do Docker local. Os 1.078 trechos gravados nas 108 operações foram comparados com a matriz recalculada, e todos são idênticos em distância, velocidade e declividade.
- **Sementes do AG:** a API envia ao otimizador uma semente derivada dos ids dos pontos, na ordem enviada (`RouteProcessor.seedOf`: começa em 17 e faz `semente × 31 + id` para cada ponto). Os parâmetros do AG eram os padrões: população 300, 500 gerações, cruzamento 0,9 e mutação 0,4. O veículo tinha 7.500 kg, carregado.
- **Rotas:** `reproduzir.py` roda o AG de novo com essas matrizes, sementes e parâmetros. Em 2026-11-26, as 108 rotas (54 ensaios, dois critérios) saíram iguais às gravadas em 2026-10-19, ponto a ponto, e com a mesma emissão total. Assim, cada número do `execucoes.csv` pode ser refeito a partir deste pacote.

## Ensaios por origem e por tamanho

Ganho de emissão da rota de menor emissão sobre a de menor distância, em porcentagem: média de 3 ensaios por célula, com o mínimo e o máximo entre parênteses.

| Origem | 5 pontos | 10 pontos | 14 pontos | Todas |
|---|---|---|---|---|
| Consolação | 14,72% (6,30 a 24,91) | 10,50% (2,19 a 18,80) | 21,78% (19,06 a 24,65) | 15,67% |
| Paulista-Trianon | 9,45% (2,27 a 19,09) | 10,56% (0,00 a 15,85) | 14,46% (7,56 a 24,14) | 11,49% |
| Vila Mariana | 17,26% (7,69 a 22,79) | 13,34% (8,34 a 17,42) | 9,19% (5,51 a 15,48) | 13,26% |
| Pinheiros | 4,92% (0,00 a 14,75) | 9,09% (0,00 a 16,49) | 17,34% (12,47 a 20,03) | 10,45% |
| Mooca | 3,38% (0,00 a 7,58) | 12,02% (0,99 a 17,64) | 12,87% (12,47 a 13,67) | 9,42% |
| Santana | 10,84% (0,83 a 22,57) | 15,15% (13,72 a 17,23) | 4,90% (0,88 a 12,95) | 10,30% |
| **Todas** | 10,10% | 11,78% | 13,43% | 11,77% |

Os 5 ensaios sem ganho (as duas rotas iguais) são os de número 15 (Paulista-Trianon, 10 pontos), 29 e 30 (Pinheiros, 5 pontos), 31 (Pinheiros, 10 pontos) e 39 (Mooca, 5 pontos). Com 3 ensaios por célula, as médias por célula são descritivas: a amplitude dentro de uma mesma célula chega a 20 pontos percentuais.

Os sorteios reaproveitam os mesmos 15 pontos de entrega em todas as origens. Por isso, os ensaios de 14 pontos de origens diferentes visitam quase os mesmos lugares, e o que muda é o ponto de saída.

## Como repetir

Do zero, a partir do pacote (cerca de 18 minutos):

```bash
python reproducao/ruas-reais/reproduzir.py
```

Para recalcular as matrizes, com o Docker do projeto no ar (o container do otimizador está na mesma rede do OSRM e do serviço de elevação):

```bash
docker compose -f ../lv-api/deploy/docker-compose.yml cp reproducao/ruas-reais/pontos.json optimizer:/tmp/pontos.json
docker compose -f ../lv-api/deploy/docker-compose.yml cp reproducao/ruas-reais/matrizes_ruas_reais.py optimizer:/tmp/matrizes.py
docker compose -f ../lv-api/deploy/docker-compose.yml exec -T optimizer python /tmp/matrizes.py --points /tmp/pontos.json > pares.json
```

O resultado só é igual ao deste pacote com o mesmo recorte do OpenStreetMap, o mesmo perfil do OSRM e o mesmo bloco SRTM registrados no `reproducao/LEIAME.md`.
