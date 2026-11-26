# Soluções de referência para as instâncias sintéticas (item L03)

Gerado em 2026-11-26 por `experiments/reference_heuristics.py`, na `main` em `6bc69dd`, com Python 3.10.11 e NumPy 1.26.4 (Intel Core i7-10700F). As instâncias são as do experimento do TCC, `synthetic_instance(n, seed=n)` para n = 10, 15, 20, 25 e 30, e os custos de cada trecho são as mesmas matrizes que o algoritmo genético usa: a emissão do modelo MEET (`SegmentEmissionFitnessFunction`, caminhão de 7.500 kg carregado) e a distância em linha reta, com a rota aberta saindo do depósito (ponto 0).

## Métodos

- **Vizinho mais próximo (VMP):** sai do depósito e vai sempre ao ponto ainda não visitado com o menor custo de trecho.
- **VMP + 2-opt:** a partir do VMP, inverte trechos da rota (sem mexer no depósito) enquanto alguma inversão reduz o custo; aceita a primeira melhora e recomeça. Como os custos são assimétricos (a declividade e a velocidade mudam com o sentido), cada candidata é avaliada pela rota inteira.
- **Ótimo exato (só 10 pontos):** avalia todas as 9! = 362.880 ordens de visita dos nove pontos depois do depósito e fica com a de menor custo. Levou 0,35 s por critério.
- **AG:** os valores das rodadas que já estão no repositório: a configuração padrão de 2026-11-07 (população 300, 500 gerações, `resultados-padrao-2026-11-07`, idêntica à Tabela 1 do TCC) e a rodada de 2.000 gerações (`resultados-tcc-2000`). "Melhor" e "média" são sobre as sementes 1, 2 e 3.

## Resultados

### Critério de emissão (kg de CO₂)

| Instância | VMP | VMP + 2-opt | Ótimo exato | AG padrão (melhor / média) | AG 2.000 ger. (melhor / média) | AG padrão (média) vs VMP + 2-opt |
|---|---|---|---|---|---|---|
| sintetica-10 | 6,0953 | 5,2206 | 3,9092 | 3,9092 / 3,9092 | 3,9092 / 3,9092 | −25,12% |
| sintetica-15 | 7,2395 | 6,0943 | — | 5,3760 / 5,5170 | 5,3760 / 5,4238 | −9,47% |
| sintetica-20 | 7,6169 | 7,2025 | — | 5,0617 / 5,1060 | 5,0617 / 5,1019 | −29,11% |
| sintetica-25 | 8,9963 | 8,8124 | — | 7,7540 / 8,1549 | 7,5218 / 7,6609 | −7,46% |
| sintetica-30 | 10,1574 | 9,6213 | — | 8,5185 / 8,7478 | 7,5568 / 7,9398 | −9,08% |

### Critério de distância (km)

| Instância | VMP | VMP + 2-opt | Ótimo exato | AG padrão (melhor / média) | AG 2.000 ger. (melhor / média) | AG padrão (média) vs VMP + 2-opt |
|---|---|---|---|---|---|---|
| sintetica-10 | 9,6467 | 8,9922 | 8,9922 | 8,9922 / 8,9922 | 8,9922 / 8,9922 | 0,00% |
| sintetica-15 | 13,5973 | 11,2098 | — | 11,2927 / 11,5449 | 11,2098 / 11,2374 | +2,99% |
| sintetica-20 | 12,8041 | 12,0963 | — | 11,9120 / 12,0929 | 11,9120 / 11,9750 | −0,03% |
| sintetica-25 | 15,9292 | 15,8070 | — | 15,5778 / 15,7861 | 15,2375 / 15,5239 | −0,13% |
| sintetica-30 | 15,6670 | 15,0239 | — | 15,5586 / 16,1993 | 15,1859 / 15,3539 | +7,82% |

Valores negativos na última coluna: o AG ficou abaixo (melhor) da referência; positivos: acima.

## Leitura

1. **Na instância de 10 pontos, o AG achou o ótimo nos dois critérios**, nas três sementes e nas duas configurações. O ótimo exato de emissão e o de distância são a mesma rota (0, 9, 7, 2, 4, 5, 3, 1, 8, 6), o que explica o Δ de 0% dessa instância no TCC: não existe, nela, rota de emissão menor que a mais curta.
2. **No critério de emissão, o AG foi melhor que o VMP + 2-opt em todas as instâncias**, de 7,46% a 29,11% na média. O 2-opt é uma busca fraca com custos assimétricos como os da emissão, em que inverter um trecho muda o sentido de todas as subidas e descidas dele.
3. **No critério de distância, o VMP + 2-opt foi melhor que a média do AG padrão nas instâncias de 15 (2,99%) e de 30 pontos (7,82%)**; nas de 20 e 25, os dois praticamente empatam. Com 2.000 gerações, a diferença diminui (0,25% na de 15 pontos e 2,20% na de 30, na média), mas o VMP + 2-opt continua melhor na de 30 pontos, inclusive que a melhor semente do AG.

## Sensibilidade do Δ à rota de distância

O Δ do TCC compara a rota de emissão do AG com a rota de distância do mesmo AG. Como a rota de distância do AG padrão não é a mais curta em todas as instâncias, o quadro abaixo recalcula o Δ usando como base a rota de distância do VMP + 2-opt (a emissão dessa rota é a coluna `nn_2opt_other_criterion` do CSV):

| Instância | Δ do TCC (AG × AG, média) | Emissão da rota de distância VMP + 2-opt (kg) | Δ com essa rota como base |
|---|---|---|---|
| sintetica-10 | 0,00% | 3,9092 | 0,00% |
| sintetica-15 | 10,14% | 5,7101 | 3,38% |
| sintetica-20 | 27,01% | 7,1284 | 28,37% |
| sintetica-25 | 5,62% | 10,3702 | 21,36% |
| sintetica-30 | 1,85% | 8,4351 | −3,71% |

O Δ depende muito de qual rota curta é usada como base: rotas de distância parecida (diferença de poucos por cento) podem ter emissões bem diferentes. A média continua positiva (9,88% contra 8,92% do TCC), mas o resultado por instância muda, e a instância de 30 pontos passa a ter Δ negativo. Isso deve entrar nas ameaças à validade: o Δ mede a diferença entre duas soluções heurísticas, e não entre os ótimos dos dois critérios.

## Arquivos

- `referencias.json`: todas as linhas, com as rotas encontradas e o metadado da execução
- `referencias.csv`: as mesmas linhas, sem as rotas

## Como repetir

```bash
python -m experiments.reference_heuristics --output-dir experiments/resultados-referencia-AAAA-MM-DD
```
