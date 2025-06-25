from flask import Blueprint

from lnmt.__version__ import __version__

core = Blueprint("core", __name__)

@core.context_processor
def inject_version():
    return {"version": __version__}
