import os

import dgl
import numpy as np
import pandas as pd
import rdkit
import torch
from rdkit.Chem import GetPeriodicTable
from rdkit.Chem.Crippen import MolLogP
from rdkit.Chem.Descriptors import MolWt
from rdkit.Chem.inchi import MolFromInchi
from rdkit.Chem.Lipinski import NumHDonors
from rdkit.Chem.rdMolDescriptors import CalcTPSA
from rdkit.Chem.rdmolops import AddHs
from rdkit.Chem.rdPartialCharges import ComputeGasteigerCharges
from torch.utils.data import Dataset

ATOM_TYPES = [
    "Ag",
    "As",
    "B",
    "Br",
    "C",
    "Ca",
    "Cl",
    "F",
    "H",
    "I",
    "K",
    "Li",
    "Mg",
    "N",
    "Na",
    "O",
    "P",
    "S",
    "Se",
    "Si",
    "Te",
    "Zn",
]


CHIRALITY = [
    rdkit.Chem.rdchem.ChiralType.CHI_OTHER,
    rdkit.Chem.rdchem.ChiralType.CHI_TETRAHEDRAL_CCW,
    rdkit.Chem.rdchem.ChiralType.CHI_TETRAHEDRAL_CW,
    rdkit.Chem.rdchem.ChiralType.CHI_UNSPECIFIED,
]


HYBRIDIZATION = [
    rdkit.Chem.rdchem.HybridizationType.OTHER,
    rdkit.Chem.rdchem.HybridizationType.S,
    rdkit.Chem.rdchem.HybridizationType.SP,
    rdkit.Chem.rdchem.HybridizationType.SP2,
    rdkit.Chem.rdchem.HybridizationType.SP3,
    rdkit.Chem.rdchem.HybridizationType.SP3D,
    rdkit.Chem.rdchem.HybridizationType.SP3D2,
    rdkit.Chem.rdchem.HybridizationType.UNSPECIFIED,
]


def mol_to_dgl(mol):
    """
    Converts mol to featurized DGL graph.
    """
    g = dgl.DGLGraph()
    g.add_nodes(mol.GetNumAtoms())
    g.set_n_initializer(dgl.init.zero_initializer)
    g.set_e_initializer(dgl.init.zero_initializer)

    features = []

    pd = GetPeriodicTable()
    ComputeGasteigerCharges(mol)

    for atom in mol.GetAtoms():
        atom_feat = []
        atom_type = [0] * len(ATOM_TYPES)
        atom_type[ATOM_TYPES.index(atom.GetSymbol())] = 1

        chiral = [0] * len(CHIRALITY)
        chiral[CHIRALITY.index(atom.GetChiralTag())] = 1

        ex_valence = atom.GetExplicitValence()
        charge = atom.GetFormalCharge()

        hybrid = [0] * len(HYBRIDIZATION)
        hybrid[HYBRIDIZATION.index(atom.GetHybridization())] = 1

        degree = atom.GetDegree()
        valence = atom.GetImplicitValence()
        aromatic = int(atom.GetIsAromatic())
        ex_hs = atom.GetNumExplicitHs()
        im_hs = atom.GetNumImplicitHs()
        rad = atom.GetNumRadicalElectrons()
        ring = int(atom.IsInRing())

        mass = pd.GetAtomicWeight(atom.GetSymbol())
        vdw = pd.GetRvdw(atom.GetSymbol())
        pcharge = float(atom.GetProp("_GasteigerCharge"))

        atom_feat.extend(atom_type)
        atom_feat.extend(chiral)
        atom_feat.append(ex_valence)
        atom_feat.append(charge)
        atom_feat.extend(hybrid)
        atom_feat.append(degree)
        atom_feat.append(valence)
        atom_feat.append(aromatic)
        atom_feat.append(ex_hs)
        atom_feat.append(im_hs)
        atom_feat.append(rad)
        atom_feat.append(ring)
        atom_feat.append(mass)
        atom_feat.append(vdw)
        atom_feat.append(pcharge)
        features.append(atom_feat)

    for bond in mol.GetBonds():
        g.add_edge(bond.GetBeginAtomIdx(), bond.GetEndAtomIdx())

    g.ndata["feat"] = torch.FloatTensor(features)
    return g


def get_global_features(mol):
    # MW, TPSA, logP, n.hdonors
    mw = MolWt(mol)
    tpsa = CalcTPSA(mol)
    logp = MolLogP(mol)
    n_hdonors = NumHDonors(mol)

    desc = np.array([mw, tpsa, logp, n_hdonors], dtype=np.float32)
    return desc


class GraphData(Dataset):
    def __init__(self, inchi, labels, mask):
        self.inchi = inchi
        self.labels = np.array(labels, dtype=np.float32)
        self.mask = np.array(mask, dtype=np.bool)

        assert len(self.inchi) == len(self.labels)

    def __getitem__(self, idx):
        mol = MolFromInchi(self.inchi[idx])
        mol = AddHs(mol)
        return (
            mol_to_dgl(mol),
            get_global_features(mol),
            self.labels[idx, :],
            self.mask[idx, :],
        )

    def __len__(self):
        return len(self.inchi)


def collate_pair(samples):
    graphs_i, g_feats, labels, masks = map(list, zip(*samples))
    batched_graph_i = dgl.batch(graphs_i)
    return (
        batched_graph_i,
        torch.as_tensor(g_feats),
        torch.as_tensor(labels),
        torch.as_tensor(masks),
    )


if __name__ == "__main__":
    from molexplain.utils import PROCESSED_DATA_PATH

    inchis = np.load(os.path.join(PROCESSED_DATA_PATH, "inchis.npy"))
    mol = MolFromInchi(inchis[243], sanitize=False, removeHs=False)

    from rdkit.Chem.rdmolops import AddHs
    g_feat = get_global_features(mol)
