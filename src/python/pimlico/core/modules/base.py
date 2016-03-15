"""
This module provides base classes for Pimlico modules.

The procedure for creating a new module is the same whether you're contributing a module to the core set in
the Pimlico codebase or a standalone module in your own codebase, or for a specific pipeline.

A Pimlico module is identified by the full Python-path to the Python package that contains it. This
package should be laid out as follows:
 - The module's metadata is defined by a class in info.py called ModuleInfo, which should inherit from
   BaseModuleInfo or one of its subclasses.
 - The module's functionality is provided by a class in exec.py called ModuleExecutor, which should inherit
   from BaseModuleExecutor.

The exec Python module will not be imported until an instance of the module is to be run. This means that
you can import dependencies and do any necessary initialization at the point where it's executed, without
worrying about incurring the associated costs (and dependencies) every time a pipeline using the module
is loaded.

"""
from importlib import import_module
import os

from pimlico.core.config import PipelineStructureError
from pimlico.core.modules.options import process_module_options


class BaseModuleInfo(object):
    """
    Abstract base class for all pipeline modules' metadata.

    """
    module_type_name = NotImplemented
    module_options = []
    module_inputs = []
    # Specifies a list of (name, datatype class) pairs
    module_outputs = []
    # Whether the module should be executed
    # Typically True for almost all modules, except input modules (though some of them may also require execution) and
    #  filters
    module_executable = True

    def __init__(self, module_name, pipeline, inputs={}, options={}):
        self.inputs = inputs
        self.options = options
        self.module_name = module_name
        self.pipeline = pipeline

    def __repr__(self):
        return "%s(%s)" % (self.module_type_name, self.module_name)

    @classmethod
    def process_module_options(cls, opt_dict):
        """
        Parse the options in a dictionary (probably from a config file),
        checking that they're valid for this model type.

        :param opt_dict: dict of options, keyed by option name
        :return: dict of options
        """
        module_options = dict(cls.module_options)
        return process_module_options(module_options, opt_dict, cls.module_type_name)

    @classmethod
    def extract_input_options(cls, opt_dict, module_name=None):
        """
        Given the config options for a module instance, pull out the ones that specify where the
        inputs come from and match them up with the appropriate input names.

        The inputs returned are just names as they come from the config file. They are split into
        module name and output name, but they are not in any way matched up with the modules they
        connect to or type checked.

        :param module_name: name of the module being processed, for error output. If not given, the name
            isn't included in the error.
        :return: dictionary of inputs
        """
        inputs = {}
        for opt_name, opt_value in opt_dict.items():
            if opt_name == "input":
                # Allow the name "input" to be used where there's only one input
                if len(cls.module_inputs) == 1:
                    inputs[cls.module_inputs[0][0]] = opt_dict.pop("input")
                else:
                    raise ModuleInfoLoadError(
                        "plain 'input' option was given to %s module%s, but %s modules have %d inputs. Use "
                        "'input_<input_name>' instead" % (cls.module_type_name,
                                                          (" %s" % module_name) if module_name else "",
                                                          cls.module_type_name, len(cls.module_inputs)))
            elif opt_name.startswith("input_"):
                input_name = opt_name[6:]
                if input_name not in dict(cls.module_inputs):
                    raise ModuleInfoLoadError("%s module%s got unknown input '%s'. Available inputs: %s" % (
                        cls.module_type_name, (" %s" % module_name) if module_name else "",
                        input_name, ", ".join([i[0] for i in cls.module_inputs])
                    ))
                inputs[input_name] = opt_dict.pop(opt_name)

        # Check for any inputs that weren't specified
        unspecified_inputs = set(i[0] for i in cls.module_inputs) - set(inputs.keys())
        if unspecified_inputs:
            raise ModuleInfoLoadError("%s module%s has unspecified input%s '%s'" % (
                cls.module_type_name, (" %s" % module_name) if module_name else "",
                "s" if len(unspecified_inputs) > 1 else "", ", ".join(unspecified_inputs)
            ))

        # Split up the input specifiers
        for input_name, input_spec in inputs.items():
            if "." in input_spec:
                # This is a module name + output name
                module_name, __, output_name = input_spec.rpartition(".")
            else:
                # Just a module name, using the default output
                module_name = input_spec
                output_name = None
            inputs[input_name] = (module_name, output_name)

        return inputs

    @classmethod
    def process_config(cls, config_dict, module_name=None):
        """
        Convenience wrapper to do all config processing from a dictionary of module config.

        """
        options = dict(config_dict)
        # Remove the "type" option if it's still in there
        options.pop("type", None)
        # Pull out the input options and match them up with inputs
        inputs = cls.extract_input_options(options, module_name=module_name)
        # Process the rest of the values as module options
        options = cls.process_module_options(options)
        return inputs, options

    def get_output_dir(self):
        return os.path.join(self.pipeline.short_term_store, self.module_name)

    def get_output_datatype(self, output_name=None):
        if len(self.module_outputs) == 0:
            raise PipelineStructureError("%s module has no outputs" % self.module_type_name)
        elif output_name is None:
            # Get the default output
            # Often there'll be only one output, so a name needn't be specified
            # If there are multiple, the first is the default
            output_name, datatype = self.module_outputs[0]
        else:
            outputs = dict(self.module_outputs)
            if output_name not in outputs:
                raise PipelineStructureError("%s module does not have an output named '%s'. Available outputs: %s" %
                                             (self.module_type_name, output_name, ", ".join(outputs.keys())))
            datatype = outputs[output_name]
        return output_name, datatype

    def instantiate_output_datatype(self, output_name, output_datatype):
        """
        Subclasses may want to override this to provide special behaviour for instantiating
        particular outputs' datatypes.

        """
        return output_datatype(os.path.join(self.get_output_dir(), output_name))

    def get_output(self, output_name=None):
        """
        Get a datatype instance corresponding to one of the outputs of the module.

        """
        output_name, datatype = self.get_output_datatype(output_name=output_name)
        return self.instantiate_output_datatype(output_name, datatype)

    def get_input_module_connection(self, input_name=None):
        """
        Get the ModuleInfo instance and output name for the output that connects up with a named input (or the
        first input) on this module instance. Used by get_input() -- most of the time you probably want to
        use that to get the instantiated datatype for an input.
        """
        if input_name is None:
            if len(self.module_inputs) == 0:
                raise PipelineStructureError("module '%s' doesn't have any inputs. Tried to get the first input" %
                                             self.module_name)
            input_name = self.module_inputs[0][0]
        if input_name not in self.inputs:
            raise PipelineStructureError("module '%s' doesn't have an input '%s'" % (self.module_name, input_name))
        previous_module_name, output_name = self.inputs[input_name]
        # Try getting hold of the module that we need the output of
        previous_module = self.pipeline[previous_module_name]
        return previous_module, output_name

    def get_input(self, input_name=None):
        """
        Get a datatype instance corresponding to one of the inputs to the module.
        Looks up the corresponding output from another module and uses that module's metadata to
        get that output's instance.
        If an input name is not given, the first input is returned.

        """
        previous_module, output_name = self.get_input_module_connection(input_name)
        return previous_module.get_output(output_name)

    @classmethod
    def is_input(cls):
        from pimlico.core.modules.inputs import InputModuleInfo
        return issubclass(cls, InputModuleInfo)

    @property
    def dependencies(self):
        return [module_name for (module_name, output_name) in self.inputs.values()]

    def typecheck_inputs(self):
        if self.is_input() or len(self.module_inputs) == 0:
            # Nothing to check
            return

        module_inputs = dict(self.module_inputs)
        for input_name, (dep_module_name, output) in self.inputs.items():
            # Check the type of each input in turn
            input_type_requirement = module_inputs[input_name]
            # Load the dependent module
            dep_module = self.pipeline[dep_module_name]
            # Try to load the named output (or the default, if no name was given)
            output_name, dep_module_output = dep_module.get_output_datatype(output_name=output)
            # Check that the provided output type is a subclass of (or equal to) the required input type
            if not issubclass(dep_module_output, input_type_requirement):
                raise PipelineStructureError(
                    "module %s's %s-input is required to be of %s type (or a descendent), but module %s's "
                    "%s-output provides %s" % (
                        self.module_name, input_name, input_type_requirement.__name__,
                        dep_module_name, output_name, dep_module_output.__name__
                    ))

    def check_runtime_dependencies(self):
        """
        Check that all software required to execute this module is installed and locatable. This is
        separate to metadata config checks, so that you don't need to satisfy the dependencies for
        all modules in order to be able to run one of them. You might, for example, want to run different
        modules on different machines. This is called when a module is about to be executed.
        
        Returns a list of triples: (dependency short name, module name, description/error message)
        
        Take care when overriding this that you don't put any import statements at the top of the Python 
        module that will make loading the ModuleInfo itself dependent on runtime dependencies.  
        You'll want to run import checks by putting import statements within this method.
        
        You should also call the super method for checking previous modules' dependencies.

        """
        missing_dependencies = []
        # Instantiate any input datatypes this module will need
        for input_name in self.inputs.keys():
            input_datatype = self.get_input(input_name)
            # Check the datatype's dependencies
            missing_dependencies.extend([
                (name, "%s input %s datatype" % (self.module_name, input_name), desc)
                for (name, desc) in input_datatype.check_runtime_dependencies()
            ])

        # Check the dependencies of any previous modules that are not executable: their dependencies 
        # also need to be satisfied when this one is run
        for dep_module_name in self.dependencies:
            dep_module = self.pipeline[dep_module_name]
            if not dep_module.module_executable:
                missing_dependencies.extend(dep_module.check_runtime_dependencies())
        return missing_dependencies


class BaseModuleExecutor(object):
    """
    Abstract base class for executors for Pimlico modules. These are classes that actually
    do the work of executing the module on given inputs, writing to given output locations.

    """
    def execute(self, module_instance_info):
        raise NotImplementedError


class ModuleInfoLoadError(Exception):
    pass


class ModuleExecutorLoadError(Exception):
    pass


class ModuleTypeError(Exception):
    pass


class DependencyError(Exception):
    """
    Raised when a module's dependencies are not satisfied. Generally, this means a dependency library
    needs to be installed, either on the local system or (more often) by calling the appropriate
    make target in the lib directory.

    """
    pass


def load_module_executor(path):
    """
    Utility for loading the executor class for a module from its full path.
    Just a wrapper around an import, with some error checking.

    :param path: path to Python package containing the module
    :return: class
    """
    # First import the metadata class
    module_info = load_module_info(path)
    # Check this isn't an input module: they shouldn't be executed
    if module_info.module_executable:
        raise ModuleExecutorLoadError("%s module type is not an executable module. It can't be (and doesn't need "
                                      "to be) executed: execute the next module in the pipeline" %
                                      module_info.module_type_name)

    executor_path = "%s.exec" % path
    try:
        mod = import_module(executor_path)
    except ImportError:
        raise ModuleInfoLoadError("module %s could not be loaded, could not import path %s" % (path, executor_path))
    if not hasattr(mod, "ModuleExecutor"):
        raise ModuleExecutorLoadError("could not load class %s.ModuleExecutor" % executor_path)
    return mod.ModuleExecutor


def load_module_info(path):
    """
    Utility to load the metadata for a Pimlico pipeline module from its package Python path.

    :param path:
    :return:
    """
    info_path = "%s.info" % path
    try:
        mod = import_module(info_path)
    except ImportError:
        raise ModuleInfoLoadError("module %s could not be imported, could not import %s" % (path, info_path))

    if not hasattr(mod, "ModuleInfo"):
        raise ModuleInfoLoadError("could not load class %s.ModuleInfo" % info_path)
    return mod.ModuleInfo
