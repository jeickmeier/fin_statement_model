"""Centralized logging configuration for the fin_statement_model library."""

import logging

# Attach a NullHandler to the base fin_statement_model logger so that
# all child loggers inherit it and avoid 'No handler' warnings by default.
logging.getLogger("fin_statement_model").addHandler(logging.NullHandler())
