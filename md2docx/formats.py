"""Format support helpers for md2docx.

Defines supported output formats by input extension and maps file extensions to
pandoc reader names. Reuse across views, signals, and management command.
"""

SUPPORTED_OUTPUTS = {
    'md': ['docx', 'pdf', 'html', 'odt', 'rtf', 'tex', 'epub'],
    'markdown': ['docx', 'pdf', 'html', 'odt', 'rtf', 'tex', 'epub'],
    'docx': ['md', 'pdf', 'html', 'odt', 'rtf', 'tex'],
    'html': ['md', 'pdf', 'docx', 'odt'],
    'htm': ['md', 'pdf', 'docx', 'odt'],
    'tex': ['pdf', 'docx', 'md'],
    'rtf': ['md', 'docx', 'pdf'],
    'odt': ['md', 'docx', 'pdf'],
    'epub': ['md', 'docx', 'pdf'],
    'pdf': ['md', 'docx', 'html'],  # limited, included for completeness
}

# Map input file extensions to pandoc reader names
INPUT_READERS = {
    'md': 'markdown',
    'markdown': 'markdown',
    'txt': 'markdown',
    'docx': 'docx',
    'html': 'html',
    'htm': 'html',
    'rtf': 'rtf',
    'odt': 'odt',
    'tex': 'latex',
    'epub': 'epub',
    'pdf': 'pdf',  # pandoc pdf reader limited; kept for completeness
}

DEFAULT_OUTPUT = 'docx'
DEFAULT_INPUT_READER = 'markdown'


def allowed_outputs(input_ext: str):
    input_ext = (input_ext or '').lower()
    return SUPPORTED_OUTPUTS.get(input_ext, [DEFAULT_OUTPUT])


def input_reader_for(ext: str):
    return INPUT_READERS.get((ext or '').lower(), DEFAULT_INPUT_READER)
