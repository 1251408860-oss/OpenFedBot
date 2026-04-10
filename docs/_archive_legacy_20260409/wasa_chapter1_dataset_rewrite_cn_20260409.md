# 第一章数据集口径改写版

以下内容可直接放入第一章引言中与数据集相关的位置。

本文的评估范围被有意限定在基准内部。我们使用 Ca-Bench 的两个图场景开展实验，分别为 `scenario_e_three_tier_high2` 和 `scenario_h_mimic_heavy_overlap`。这两个场景来自一篇当前仍在投稿、尚未录用的 benchmark 论文。因此，本文不将其表述为公开数据集，也不将其表述为公开基准。基于这两个场景，我们构建了面向 `burst`、`slowburn` 和 `mimic` 三类 bot family 的 leave-one-family-out open-world protocols，并同时考察 same-scenario 与 cross-scenario 两种部署设置。由此，本文的实验结论应理解为该 benchmark 范围内的部署证据，而不是多个独立公开数据集上的广泛泛化结论。

如果需要拆成单句替换，可优先使用以下版本。

1. 本文的评估范围被有意限定在基准内部。
2. 我们使用 Ca-Bench 的两个图场景开展实验，分别为 `scenario_e_three_tier_high2` 和 `scenario_h_mimic_heavy_overlap`。
3. 这两个场景来自一篇当前仍在投稿、尚未录用的 benchmark 论文，因此本文不将其表述为公开数据集或公开基准。
4. 基于这两个场景，我们构建了面向 `burst`、`slowburn` 和 `mimic` 三类 bot family 的 leave-one-family-out open-world protocols，并同时考察 same-scenario 与 cross-scenario 两种部署设置。
5. 本文的实验结论应理解为该 benchmark 范围内的部署证据，而不是多个独立公开数据集上的广泛泛化结论。
6. 为保证复现性，我们固定了本地图结构契约以及与当前 Ca-Bench 投稿版本对应的场景快照，使实验管线不依赖持续变化的上游构建过程。
7. 本文的局限也需要明确写出。当前评估只覆盖该 benchmark 投稿中的两个场景及其对应图构建流程，因此不能支持强意义上的跨数据集泛化声明。
