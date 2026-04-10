from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv


class GraphSAGEClassifier(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int, out_dim: int, dropout: float = 0.2):
        super().__init__()
        self.conv1 = SAGEConv(in_dim, hidden_dim)
        self.conv2 = SAGEConv(hidden_dim, hidden_dim)
        self.classifier = nn.Linear(hidden_dim, out_dim)
        self.dropout = float(dropout)

    def encode(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        h = F.relu(self.conv1(x, edge_index))
        h = F.dropout(h, p=self.dropout, training=self.training)
        h = self.conv2(h, edge_index)
        return h

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        *,
        return_embeddings: bool = False,
    ) -> torch.Tensor | tuple[torch.Tensor, torch.Tensor]:
        embeddings = self.encode(x, edge_index)
        logits = self.classifier(F.relu(embeddings))
        if return_embeddings:
            return logits, embeddings
        return logits
