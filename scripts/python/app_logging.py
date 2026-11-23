# -*- coding: utf-8 -*-
from __future__ import annotations
import logging
from pathlib import Path
from config_loader import ROOT

_LOG = None

def get_logger(name: str = "gguf_runner") -> logging.Logger:
    global _LOG
    if _LOG is not None:
        return logging.getLogger(name)
    log_dir = ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "app.log"
    logger = logging.getLogger("gguf_runner")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(path, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(fh)
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        sh.setLevel(logging.WARNING)
        logger.addHandler(sh)
    _LOG = logger
    return logging.getLogger(name)
