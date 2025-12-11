# Verification tools
import sys
import io
import unittest
import ast
from typing import Dict, Any, List
from tools.base import Tool


# Standard library modules that are safe to import
STDLIB_MODULES = {
    # Built-ins and core
    'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat', 'asyncio', 'asyncore',
    'atexit', 'base64', 'bdb', 'binascii', 'binhex', 'bisect', 'builtins',
    'bz2', 'calendar', 'cgi', 'cgitb', 'chunk', 'cmath', 'cmd', 'code',
    'codecs', 'codeop', 'collections', 'colorsys', 'compileall', 'concurrent',
    'configparser', 'contextlib', 'contextvars', 'copy', 'copyreg', 'cProfile',
    'crypt', 'csv', 'ctypes', 'curses', 'dataclasses', 'datetime', 'dbm',
    'decimal', 'difflib', 'dis', 'distutils', 'doctest', 'email', 'encodings',
    'enum', 'errno', 'faulthandler', 'fcntl', 'filecmp', 'fileinput', 'fnmatch',
    'fractions', 'ftplib', 'functools', 'gc', 'getopt', 'getpass', 'gettext',
    'glob', 'graphlib', 'grp', 'gzip', 'hashlib', 'heapq', 'hmac', 'html',
    'http', 'idlelib', 'imaplib', 'imghdr', 'imp', 'importlib', 'inspect',
    'io', 'ipaddress', 'itertools', 'json', 'keyword', 'lib2to3', 'linecache',
    'locale', 'logging', 'lzma', 'mailbox', 'mailcap', 'marshal', 'math',
    'mimetypes', 'mmap', 'modulefinder', 'multiprocessing', 'netrc', 'nis',
    'nntplib', 'numbers', 'operator', 'optparse', 'os', 'ossaudiodev',
    'pathlib', 'pdb', 'pickle', 'pickletools', 'pipes', 'pkgutil', 'platform',
    'plistlib', 'poplib', 'posix', 'posixpath', 'pprint', 'profile', 'pstats',
    'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc', 'queue', 'quopri', 'random',
    're', 'readline', 'reprlib', 'resource', 'rlcompleter', 'runpy', 'sched',
    'secrets', 'select', 'selectors', 'shelve', 'shlex', 'shutil', 'signal',
    'site', 'smtpd', 'smtplib', 'sndhdr', 'socket', 'socketserver', 'spwd',
    'sqlite3', 'ssl', 'stat', 'statistics', 'string', 'stringprep', 'struct',
    'subprocess', 'sunau', 'symtable', 'sys', 'sysconfig', 'syslog', 'tabnanny',
    'tarfile', 'telnetlib', 'tempfile', 'termios', 'test', 'textwrap', 'threading',
    'time', 'timeit', 'tkinter', 'token', 'tokenize', 'trace', 'traceback',
    'tracemalloc', 'tty', 'turtle', 'turtledemo', 'types', 'typing', 'unicodedata',
    'unittest', 'urllib', 'uu', 'uuid', 'venv', 'warnings', 'wave', 'weakref',
    'webbrowser', 'winreg', 'winsound', 'wsgiref', 'xdrlib', 'xml', 'xmlrpc',
    'zipapp', 'zipfile', 'zipimport', 'zlib',
    # Common typing imports
    'typing_extensions',
}


class LinterTool(Tool):
    """Tool to check Python code syntax, imports, and basic style using AST"""
    
    @property
    def name(self) -> str:
        return "linter"
    
    @property
    def description(self) -> str:
        return "Analyzes Python code for syntax errors, invalid imports, and structural issues. Use before running code."
    
    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "path": {
                "type": "string",
                "description": "Path to the .py file to lint"
            }
        }
    
    def execute(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Syntax Check
            try:
                ast.parse(code)
            except SyntaxError as e:
                return {
                    "success": False,
                    "error": f"SyntaxError on line {e.lineno}: {e.msg}",
                    "valid_syntax": False
                }
            
            # Parse AST for analysis
            tree = ast.parse(code)
            issues = []
            invalid_imports = []
            
            for node in ast.walk(tree):
                # Check for empty except blocks (bad practice)
                if isinstance(node, ast.ExceptHandler):
                    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                        issues.append(f"Line {node.lineno}: Empty except block (silent failure)")
                
                # Check for invalid imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split('.')[0]
                        if module_name not in STDLIB_MODULES:
                            invalid_imports.append(f"Line {node.lineno}: Cannot import '{alias.name}' - not in standard library")
                
                if isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_name = node.module.split('.')[0]
                        if module_name not in STDLIB_MODULES:
                            invalid_imports.append(f"Line {node.lineno}: Cannot import from '{node.module}' - not in standard library")
            
            # Return error if invalid imports found
            if invalid_imports:
                return {
                    "success": False,
                    "error": "Invalid imports detected. You must define all functions locally.\n" + "\n".join(invalid_imports),
                    "valid_syntax": True,
                    "invalid_imports": invalid_imports,
                    "hint": "Define the required functions directly in your code instead of importing."
                }
            
            return {
                "success": True,
                "valid_syntax": True,
                "issues": issues,
                "message": "Syntax OK" if not issues else f"Syntax OK but found {len(issues)} issues"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


class TestRunnerTool(Tool):
    """Tool to run specific unit tests"""
    
    @property
    def name(self) -> str:
        return "run_tests"
    
    @property
    def description(self) -> str:
        return "Runs a test file (unittest or pytest style) and returns the results."
    
    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "path": {
                "type": "string",
                "description": "Path to the test file"
            }
        }
    
    def execute(self, path: str) -> Dict[str, Any]:
        import subprocess
        try:
            # Run via subprocess to avoid polluting current process space
            # and to handle segfaults/infinite loops safely
            cmd = [sys.executable, path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Test execution timed out (30s)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

def register_verify_tools():
    from tools.registry import get_registry
    registry = get_registry()
    registry.register(LinterTool())
    registry.register(TestRunnerTool())
