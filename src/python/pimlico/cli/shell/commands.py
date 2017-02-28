"""
Basic set of shell commands that are always available.

"""
from pimlico.cli.shell.base import ShellCommand


class MetadataCmd(ShellCommand):
    commands = ["metadata"]
    help_text = "Display the loaded dataset's metadata"

    def execute(self, shell, *args, **kwargs):
        metadata = shell.data.metadata
        print "\n".join("%s: %s" % (key, val) for (key, val) in metadata.iteritems())


class PythonCmd(ShellCommand):
    commands = ["python", "py"]
    help_text = "Run a Python interpreter using the current environment, including import availability of " \
                "all the project code, as well as the dataset in the 'data' variable"

    def execute(self, shell, *args, **kwargs):
        from code import interact
        import sys
        # Customize the prompt so we see that we're in the interpreter
        sys.ps1 = "py>> "
        sys.ps2 = "py.. "
        print "Entering Python interpreter. Type Ctrl+D to exit\n"
        # Enter the interpreter
        interact(local=shell.env)
        print "Leaving Python interpreter"


BASIC_SHELL_COMMANDS = [MetadataCmd(), PythonCmd()]
