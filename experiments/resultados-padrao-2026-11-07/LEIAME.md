# Rodada da configuração padrão com a linha de base aleatória

Executada em 2026-11-07, de 20:16:04 a 20:22:22 UTC, a partir de `main` (`c008c72`), com `git status` limpo.

```bash
python -m experiments.run_experiment --output-dir experiments/resultados-padrao-2026-11-07
python -m experiments.run_experiment --resummarize experiments/resultados-padrao-2026-11-07
```

O primeiro comando usa os parâmetros padrão do sistema: população 300, 500 gerações, cruzamento 0,9 e mutação 0,4. As instâncias são as sintéticas de 10, 15, 20, 25 e 30 pontos, geradas com semente igual ao número de pontos. Cada uma roda com as sementes 1, 2 e 3 do AG, nos dois critérios. O segundo comando só refaz o `resumo.json` com os campos por instância, sem rodar de novo.

Ambiente: Intel Core i7-10700F (8 núcleos, 16 threads, 2,9 GHz), 15,9 GB de RAM, Windows 11 Pro 26200, Python 3.10.11, numpy 1.26.4. O script roda em um único processo, uma execução depois da outra; o pool de processos da API não é usado.

## Arquivos

- `execucoes.csv`: uma linha por instância e semente, sem arredondamento.
- `execucoes.json`: o mesmo, mais as sequências e as curvas de convergência.
- `resumo.json`: por instância, delta médio e desvio, aumento de distância, tempo médio de cada critério, geração de convergência (média e máxima) e razão emissão do AG / média aleatória (média, desvio, mínimo e máximo).

## Resultado

| n | Δ médio ± desvio (%) | Aumento de distância (%) | Tempo MD (s) | Tempo ME (s) | Convergência média / máxima | Razão AG / aleatória: média (desvio) [mín–máx] |
|---|---|---|---|---|---|---|
| 10 | 0,00 ± 0,00 | 0,00 | 11,9 | 11,7 | 68 / 95 | 0,364 (0,001) [0,363–0,365] |
| 15 | 10,14 ± 1,04 | 12,76 | 12,1 | 12,0 | 217 / 397 | 0,387 (0,013) [0,377–0,406] |
| 20 | 27,01 ± 9,17 | 18,35 | 12,2 | 12,4 | 205 / 354 | 0,277 (0,003) [0,274–0,282] |
| 25 | 5,62 ± 1,04 | 41,90 | 12,8 | 12,8 | 317 / 499 | 0,324 (0,015) [0,308–0,344] |
| 30 | 1,85 ± 1,95 | 46,31 | 12,7 | 12,4 | 433 / 470 | 0,302 (0,010) [0,295–0,316] |

- 3 de 5 instâncias com Δ médio ≥ 5%; Δ médio geral de 8,92%; aumento médio de distância de 23,87%.
- O desvio é o populacional (numpy `std`) entre as três sementes.
- Linha de base aleatória: 1.000 ordens de visita por instância e semente, sorteadas com `default_rng([7919, semente])`, gerador separado do AG. A emissão da rota do AG fica entre 27,4% e 40,6% da média aleatória, abaixo da meta de 90% do KPI-6 em todas as execuções.

## Comparação com a Tabela 1 do TCC

As 15 execuções são idênticas à Tabela 1 em distância MD, emissão MD, distância ME, emissão ME e Δ, com duas casas decimais. Só o tempo difere: 9,1 a 9,9 s na Tabela 1 contra 11,6 a 12,9 s aqui.

## De onde vêm as diferenças de tempo

A mesma conta, com as mesmas sementes e o mesmo resultado, leva tempos diferentes conforme a máquina e o ambiente. Medição feita com a instância de 30 pontos, semente 1, critério de emissão e 2.000 gerações:

| Código | Onde | Tempo | Emissão |
|---|---|---|---|
| 18/10 (`0e003c3`) | este computador, Windows, Python 3.10.11 | 47,0 s | 8,339455 kg |
| atual (`c008c72`) | este computador, Windows, Python 3.10.11 | 46,2 s | 8,339455 kg |
| atual (`c008c72`) | este computador, contêiner Linux do Docker Compose (Python 3.11.18, 4 CPUs) | 40,1 s | 8,339455 kg |

- O código não ficou mais lento entre 18/10 e hoje: 47,0 s e 46,2 s na mesma máquina.
- Os cerca de 12 s por execução de `experiments/resultados/` (18/10, 2.000 gerações) foram medidos no computador do André, autor do commit `0e003c3`.
- Os 38,7 s de média (máximo de 41,6 s) que o TCC cita para 2.000 gerações correspondem ao contêiner Linux deste computador (40,1 s medidos agora para n = 30).
- Os 9,1 a 9,9 s da Tabela 1 (500 gerações) também são compatíveis com o contêiner (cerca de 13% mais rápido que o Windows deste computador).
- O KPI-1 (menos de 60 s) depende do hardware: com 500 gerações há folga em qualquer uma das três máquinas; com 2.000 gerações, este computador fica entre 40 e 47 s.
