from pimlico.core.modules.base import BaseModuleInfo
from pimlico.datatypes.arrays import ScipySparseMatrix
from pimlico.datatypes.features import IndexedTermFeatureListCorpus


class ModuleInfo(BaseModuleInfo):
    module_type_name = "term_feature_matrix_builder"
    module_inputs = [
        ("data", IndexedTermFeatureListCorpus)
    ]
    module_outputs = [("matrix", ScipySparseMatrix)]
    module_options = {}

    def check_runtime_dependencies(self):
        missing_dependencies = []
        try:
            import numpy
        except ImportError:
            missing_dependencies.append(("Numpy", self.module_name,
                                         "install Numpy systemwide (e.g. package 'python-numpy' on Ubuntu)"))
        try:
            import scipy
        except ImportError:
            missing_dependencies.append(("Scipy", self.module_name,
                                         "install Scipy systemwide (e.g. package 'python-scipy' on Ubuntu)"))

        missing_dependencies.extend(super(ModuleInfo, self).check_runtime_dependencies())
        return missing_dependencies
