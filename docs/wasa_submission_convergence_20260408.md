# WASA 投稿实验收敛说明（2026-04-08）

## 1. 当前建议作为论文主引用的结果目录

- `clean canonical digest`:
  `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z`
- `stress robustness digest`:
  `/home/user/workspace/OpenFedBot/results/reinforced_digest_20260408T034757Z`

说明：

- `clean canonical digest` 用来写主表、主图、deployment 代价和阈值选择。
- `stress robustness digest` 用来写扰动鲁棒性与 supplement，不要拿它的 `paper_deployment_summary.csv` 当真实部署耗时，因为它来自含 7 个 perturbation 的 stress run。

## 2. 目前最稳的 paper mainline

- `safe auto backbone`:
  `cpd_shift_multiproto_consensus_plus`
- `deployment operating policy`:
  `triage_shift_multiproto_coverage_switch_plus_ova_nonbenign`
- `aggressive appendix comparator`:
  `cpd_shift_multiproto_consensus_gate_plus`

论文叙事建议：

- 方法层不要写成“单一 auto detector 全面压制全部基线”。
- 更稳的写法是：“multi-prototype open-world representation + safe auto backbone + low-benign-review deployment policy”。

## 3. 现在可以稳定写进主文的 clean 数字

来源：

- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_main_method_summary.csv`
- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_main_triage_summary.csv`
- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_review_load_summary.csv`
- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/paper_deployment_summary.csv`

`safe auto backbone`:

- cross:
  `coverage = 0.1513`, `selective_risk = 0.2398`, `unknown_misroute = 0.0128`
- same:
  `coverage = 0.2154`, `selective_risk = 0.0342`, `unknown_misroute = 0.0164`

`deployment operating policy`:

- cross:
  `actionable_coverage = 0.4773`, `safe_unknown_handling = 0.9779`, `review_benign_rate = 0.0018`, `final_defer_rate = 0.5227`
- same:
  `actionable_coverage = 0.5793`, `safe_unknown_handling = 0.9836`, `review_benign_rate = 0.0015`, `final_defer_rate = 0.4207`

`deployment cost`:

- cross:
  `review_queue_per_1k_targets = 298.82`, `defer_queue_per_1k_targets = 522.73`, `actionable_nodes_per_sec = 2342.69`, `end_to_end_sec_per_1k_targets = 0.2043`
- same:
  `review_queue_per_1k_targets = 342.53`, `defer_queue_per_1k_targets = 420.70`, `actionable_nodes_per_sec = 490.44`, `end_to_end_sec_per_1k_targets = 1.2401`

## 4. 目前仍然存在、但已可控的 limitation

来源：

- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/hardest_cpd_consensus_protocols.csv`
- `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z/hardest_triage_consensus_ova_protocols.csv`

最难 cross auto case 仍然没有被“解决”，只是比旧版稳：

- `h_to_e_slowburn`:
  `coverage = 0.0771`, `selective_risk = 0.4342`, `unknown_misroute = 0.0565`
- `h_to_e_burst`:
  `coverage = 0.1152`, `selective_risk = 0.4553`, `unknown_misroute = 0.0000`

但是 triage 后，cross hardest 的 workload 已经可以讲 deployment story：

- `h_to_e_slowburn`:
  `actionable_coverage = 0.5798`, `review_coverage = 0.4269`, `safe_unknown = 0.9425`
- `h_to_e_burst`:
  `actionable_coverage = 0.4382`, `review_coverage = 0.2865`, `safe_unknown = 0.9996`

## 5. coverage-switch 阈值 sweep 结论

来源：

- `cov10`:
  `/home/user/workspace/OpenFedBot/results/digest_cov10/reinforced_digest_20260408T040323Z`
- `cov12`:
  `/home/user/workspace/OpenFedBot/results/digest_cov12/reinforced_digest_20260408T040419Z`
- `cov14`:
  `/home/user/workspace/OpenFedBot/results/digest_cov14/reinforced_digest_20260408T040323Z`

clean 对比结论：

- `0.10`:
  cross `actionable_coverage = 0.4761`, `safe_unknown = 0.9780`
- `0.12`:
  cross `actionable_coverage = 0.4773`, `safe_unknown = 0.9779`
- `0.14`:
  cross `actionable_coverage = 0.4801`, `safe_unknown = 0.9610`

结论：

- `0.14` 带来的 cross `actionable_coverage` 增益只有 `+0.0028`，但 cross `safe_unknown` 下降了约 `-0.0169`，不值。
- `0.10` 没有带来额外安全收益，same-domain `actionable_coverage` 还更低。
- 当前最稳阈值仍然是 `shift_hybrid_activation_coverage = 0.12`。

## 6. 现在能写和不能写的 claim

可以写：

- `deployment-safe open-world federated bot triage`
- `actionable coverage` 明显高于纯 auto safe backbone
- `safe unknown handling` 高
- `review benign burden` 很低，已经接近可部署口径
- `multi-prototype representation` 明显改善 hardest cross protocol 的 deployment 可操作性

不要写：

- `high automation` 或 `自动化率高`
- `hardest cross-shift solved`
- `主方法在所有关键指标上全面显著优于所有强基线`
- `coverage-switch 本身就是更安全的 auto detector`
- `80%+ 投稿概率已经被实验锁死`

## 7. 当前最稳的写法

标题/摘要/引言要强行贴 WASA 主轴：

- `edge-cloud AI computing`
- `smart networked applications`
- `AI-based network threat detection`

最稳表述：

- 不是“我们实现了高自动化开放世界检测”。
- 而是“我们提出了一个面向 edge/networked deployment 的开放世界联邦 bot triage framework，在保持高 safe unknown handling 的同时，把 actionable coverage 提升到可用水平，并将 benign review 负担压到极低”。
