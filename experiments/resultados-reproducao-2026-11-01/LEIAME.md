# Reprodução do experimento de 18/10/2026

Executada em 2026-11-01 (17:25 UTC), a partir de `main` (`bf63f7f`) com a linha de base aleatória separada do AG.

```bash
python -m experiments.run_experiment --output-dir experiments/resultados-reproducao-2026-11-01 \
  --population 300 --generations 2000 --crossover 0.9 --mutation 0.4
```

Ambiente: Windows 11, Python 3.10.11, numpy 1.26.4.

## Comparação com `experiments/resultados/execucoes.csv` (18/10/2026)

Colunas do AG comparadas nas 15 execuções (5 instâncias × 3 sementes): `e_distance_kg`, `e_emission_kg`, `delta_percent`, `km_distance_route`, `km_emission_route`, `generations_emission`, `converged_at_emission`.

- 12 de 15 execuções idênticas em todas as colunas.
- 3 execuções (`sintetica-10`, sementes 1 a 3) diferem só no último algarismo da distância: 8,992156548841422 km contra 8,992156548841423 km. É arredondamento de ponto flutuante na ordem da soma; emissões, delta, gerações e convergência são idênticos.
- Resultado final igual: 4 de 5 instâncias com delta médio ≥ 5%.

Os tempos (`seconds_*`) não são comparáveis: dependem da máquina. Nesta execução ficaram entre 43 e 46 s por execução, contra cerca de 12 s em 18/10. Todas chegaram às 2.000 gerações, abaixo do limite de 55 s; numa máquina mais lenta o limite pode encerrar o AG antes e mudar os resultados.

## Linha de base aleatória

Para cada instância e semente, 1.000 ordens de visita sorteadas com um gerador próprio (`default_rng([7919, semente])`), separado do gerador do AG. Colunas: `e_random_kg` (média), `e_random_std_kg`, `e_random_min_kg`, `e_random_max_kg`, `random_samples` e `ratio_to_random` (emissão da rota por emissão ÷ média aleatória).
