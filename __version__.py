"""
LNMT Version Information
"""

__version__ = '2.0.0'
__version_info__ = (2, 0, 0)
__release_date__ = '2024-01-01'
__author__ = 'LNMT Team'
__license__ = 'MIT'
__copyright__ = 'Copyright 2024 LNMT Team'

def get_version():
    """Return the current version string"""
    return __version__

def get_version_tuple():
    """Return version as a tuple of integers"""
    return __version_info__

def check_version_compatibility(required_version):
    """Check if current version meets the required version"""
    if isinstance(required_version, str):
        required_parts = tuple(map(int, required_version.split('.')))
    else:
        required_parts = required_version
    
    return __version_info__ >= required_parts