.. _command_browse:

browse
~~~~~~


*Command-line tool subcommand*

View the data output by a module.


Usage:

::

    pimlico.sh [...] browse module_name [output_name] [-h] [--skip-invalid] [--formatter FORMATTER]


Positional arguments
====================

+-------------------+--------------------------------------------------------------------------------------------------------+
| Arg               | Description                                                                                            |
+===================+========================================================================================================+
| ``module_name``   | The name (or number) of the module whose output to look at. Use 'module:stage' for multi-stage modules |
+-------------------+--------------------------------------------------------------------------------------------------------+
| ``[output_name]`` | The name of the output from the module to browse. If blank, load the default output                    |
+-------------------+--------------------------------------------------------------------------------------------------------+

Options
=======

+-------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Option                  | Description                                                                                                                                                                                                                                                                                         |
+=========================+=====================================================================================================================================================================================================================================================================================================+
| ``--skip-invalid``      | Skip over invalid documents, instead of showing the error that caused them to be invalid                                                                                                                                                                                                            |
+-------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``--formatter``, ``-f`` | When browsing iterable corpora, fully qualified class name of a subclass of DocumentBrowserFormatter to use to determine what to output for each document. You may also choose from the named standard formatters for the datatype in question. Use '-f help' to see a list of available formatters |
+-------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

