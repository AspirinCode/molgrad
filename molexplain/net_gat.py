import torch
import torch.nn as nn
import torch.nn.functional as F

import dgl
import dgl.function as fn
from dgl.nn.pytorch import GATConv, edge_softmax


class GAT(nn.Module):
    def __init__(
        self, num_layers, in_dim, num_hidden, num_classes, heads, activation, residual
    ):
        super(GAT, self).__init__()
        self.num_layers = num_layers
        self.gat_layers = nn.ModuleList()
        self.activation = activation
        self.linear = nn.Linear(heads[-1], num_classes)
        # input projection (no residual)
        self.gat_layers.append(
            GATConv(
                in_feats=in_dim,
                out_feats=num_hidden,
                num_heads=heads[0],
                residual=False,
                activation=self.activation,
            )
        )
        # hidden layers
        for l in range(1, num_layers):
            # due to multi-head, the in_dim = num_hidden * num_heads
            self.gat_layers.append(
                GATConv(
                    in_feats=num_hidden * heads[l - 1],
                    out_feats=num_hidden,
                    num_heads=heads[l],
                    residual=residual,
                    activation=self.activation,
                )
            )
        # output projection
        self.gat_layers.append(
            GATConv(
                in_feats=num_hidden * heads[-2],
                out_feats=num_classes,
                num_heads=heads[-1],
                residual=True,
                activation=None,
            )
        )

    def forward(self, g):
        h = g.ndata["feat"]
        for l in range(self.num_layers):
            h = self.gat_layers[l](g, h).flatten(1)
        # output projection
        g.ndata['h'] = self.gat_layers[-1](g, h)
        latent = dgl.sum_nodes(g, 'h').mean(axis=2)
        return self.linear(latent)


if __name__ == "__main__":
    from molexplain.net_utils import GraphData, collate_pair

    inchis = ["InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3"] * 128
    labels = [1] * 128

    gd = GraphData(inchis, labels, requires_input_grad=True)
    g, label = gd[1]

    from torch.utils.data import DataLoader

    n_feat = g.ndata["feat"].shape[1]

    net = GAT(
        num_layers=6,
        in_dim=n_feat,
        num_hidden=128,
        num_classes=1,
        heads=([12] * 6) + [32],
        activation=F.elu,
        residual=True,
    )
    out = net(g)
    out.backward()

    print(g.ndata["feat"].grad)
