from pathlib import Path

import hydra
import pytorch_lightning as pl
from loguru import logger
from omegaconf import DictConfig, OmegaConf

from data.bpr_data import BPRDataModule
from data.utils import split_data
from model.matrix_factorization import BPRMatrixFactorization
from model.model_type import ModelType
from model.poprec import PopRec
from train_and_eval.evaluate import evaluate


@hydra.main(version_base=None, config_path="../config", config_name="config")
def main(cfg: DictConfig):
    logger.info(f"\n{OmegaConf.to_yaml(cfg, resolve=True)}")

    [user_train, user_valid, user_test, num_users, num_items] = split_data(
        Path(cfg.dataset_path)
    )
    logger.info(f"Total Users: {num_users}, Total Items: {num_items}")

    if cfg.model.name == ModelType.PopRec.value:
        model = PopRec(train_u2i=user_train, num_items=num_items)

    else:
        dm = BPRDataModule(
            train_interactions=[
                (user, item) for user, items in user_train.items() for item in items
            ],
            val_interactions=[
                (user, item) for user, items in user_valid.items() for item in items
            ],
            test_interactions=[
                (user, item) for user, items in user_test.items() for item in items
            ],
            num_users=num_users,
            num_items=num_items,
            batch_size=128,
        )
        dm.setup()

        model = BPRMatrixFactorization(
            num_users=num_users,
            num_items=num_items,
            embedding_dim=cfg.model.embedding_dim,
        )

        trainer = pl.Trainer(
            accelerator="cpu", max_epochs=5, logger=False, enable_checkpointing=False
        )
        trainer.fit(model, dm)

    hit_rate, ndcg = evaluate(
        model=model,
        train_data=user_train,
        test_data=user_test,
        num_items=num_items,
    )

    logger.info(
        f"[{cfg.model.name}] Hit@{cfg.k_eval}: {hit_rate:.4f}, NDCG@{cfg.k_eval}: {ndcg:.4f}"
    )


if __name__ == "__main__":
    main()
