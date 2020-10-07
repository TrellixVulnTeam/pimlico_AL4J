# This file is part of Pimlico
# Copyright (C) 2020 Mark Granroth-Wilding
# Licensed under the GNU LGPL v3.0 - https://www.gnu.org/licenses/lgpl-3.0.en.html

from future import standard_library
standard_library.install_aliases()
from builtins import zip
from builtins import str

import os
from io import StringIO

from pimlico.core.modules.base import BaseModuleExecutor
import csv


from pimlico.old_datatypes.plotting import PlotOutputWriter


class ModuleExecutor(BaseModuleExecutor):
    def execute(self):
        # Get values and labels from the inputs
        self.log.info("Collecting data")
        inputs = self.info.get_input("values")
        labels = [result.label for result in inputs]
        values = [result.result for result in inputs]

        self.log.info("Outputting data and plotting code")
        with PlotOutputWriter(self.info.get_absolute_output_dir("plot")) as writer:
            # Prepare data to go to CSV file
            io = StringIO()
            csv_writer = csv.writer(io)
            for label, value in zip(labels, values):
                csv_writer.writerow([str(label), "%f" % value])
            writer.data = io.getvalue()

            # Use a standard template plot python file
            with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "plot_template.py"), "r") as f:
                plotting_code = f.read()
            # Remove the first line, which is a comment to explain what the file is
            plotting_code = "\n".join(plotting_code.splitlines()[1:])
            writer.plotting_code = plotting_code

        # Written the plot code and data
        # Now do the plotting
        self.log.info("Running plotter")
        plot_output = self.info.get_output("plot")
        plot_output.plot()

        self.log.info("Plot output to %s" % plot_output.pdf_path)
        self.log.info("Customize plot by editing %s and recompiling (python ploy.py)" % plot_output.script_path)
