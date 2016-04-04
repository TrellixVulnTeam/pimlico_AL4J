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
import os
from importlib import import_module
from types import FunctionType

from pimlico.core.config import PipelineStructureError
from pimlico.core.modules.options import process_module_options


class BaseModuleInfo(object):
    """
    Abstract base class for all pipeline modules' metadata.

    """
    module_type_name = NotImplemented
    module_options = []
    module_inputs = []
    # Specifies a list of (name, datatype class) pairs for outputs that are always written
    module_outputs = []
    # Specifies a list of (name, datatype class) pairs for outputs that are written only if they're specified
    #  in the "output" option or used by another module
    module_optional_outputs = []
    # Whether the module should be executed
    # Typically True for almost all modules, except input modules (though some of them may also require execution) and
    #  filters
    module_executable = True
    # If specified, this ModuleExecutor class will be used instead of looking one up in the exec Python module
    module_executor_override = None

    def __init__(self, module_name, pipeline, inputs={}, options={}, optional_outputs=[]):
        self.inputs = inputs
        self.options = options
        self.module_name = module_name
        self.pipeline = pipeline

        self.default_output_name = (self.module_outputs+self.module_optional_outputs)[0][0]

        # Work out what outputs this module will make available
        if len(self.module_outputs + self.module_optional_outputs) == 0:
            # Need at least one output
            if len(self.module_optional_outputs):
                raise PipelineStructureError(
                    "module %s has no outputs. Select at least one optional output from [%s] using the 'output' option"
                    % (self.module_name, ", ".join(name for name, dt in self.module_optional_outputs))
                )
            else:
                raise PipelineStructureError("module %s defines no outputs" % self.module_name)
        # The basic outputs are always available
        self.available_outputs = list(self.module_outputs)
        # Others may be requested in the config, given to us in optional_outputs
        # Also include those that are used as inputs to other modules
        used_output_names = self.pipeline.used_outputs.get(self.module_name, [])
        # Replace None with the default output name (which could be an optional output if no non-optional are defined)
        used_output_names = set([name if name is not None else self.default_output_name for name in used_output_names])
        # Include all of these outputs in the final output list
        self.available_outputs.extend((name, dt) for (name, dt) in self.module_optional_outputs
                                      if name in set(optional_outputs)|used_output_names)

        self._metadata = None

    def __repr__(self):
        return "%s(%s)" % (self.module_type_name, self.module_name)

    @property
    def metadata_filename(self):
        return os.path.join(self.get_module_output_dir(), "metadata")

    def get_metadata(self):
        if self._metadata is None:
            # Try loading metadata
            self._metadata = {}
            if os.path.exists(self.metadata_filename):
                with open(self.metadata_filename, "r") as f:
                    for line in f:
                        if line:
                            attr, __, val = line.partition(": ")
                            self._metadata[attr.strip().lower()] = val.strip()
        return self._metadata

    def set_metadata_value(self, attr, val):
        self.set_metadata_values({attr: val})

    def set_metadata_values(self, val_dict):
        # Make sure we've got an output directory to output the metadata to
        if not os.path.exists(self.get_module_output_dir()):
            os.makedirs(self.get_module_output_dir())
        # Load the existing metadata
        metadata = self.get_metadata()
        # Add our new values to it
        metadata.update(val_dict)
        # Write the whole thing out to the file
        with open(self.metadata_filename, "w") as f:
            for attr, val in metadata.items():
                f.write("%s: %s\n" % (attr, val))

    def __get_status(self):
        # Check the metadata for current module status
        return self.get_metadata().get("status", "UNEXECUTED")

    def __set_status(self, status):
        self.set_metadata_value("status", status)

    status = property(__get_status, __set_status)

    @property
    def input_names(self):
        return [name for name, __ in self.module_inputs]

    @property
    def output_names(self):
        return [name for name, __ in self.available_outputs]

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

    @staticmethod
    def get_extra_outputs_from_options(options):
        """
        Normally, which optional outputs get produced by a module depend on the 'output' option given in the
        config file, plus any outputs that get used by subsequent modules. By overriding this method, module
        types can add extra outputs into the list of those to be included, conditional on other options.

        E.g. the corenlp module include the 'annotations' output if annotators are specified, so that the
        user doesn't need to give both options.

        """
        return []

    @classmethod
    def process_config(cls, config_dict, module_name=None):
        """
        Convenience wrapper to do all config processing from a dictionary of module config.

        """
        options = dict(config_dict)
        # Remove the "type" option if it's still in there
        options.pop("type", None)
        # Pull out the output option if it's there, to specify optional outputs
        output_opt = options.pop("output", "")
        outputs = output_opt.split(",") if output_opt else []
        # Pull out the input options and match them up with inputs
        inputs = cls.extract_input_options(options, module_name=module_name)
        # Process the rest of the values as module options
        options = cls.process_module_options(options)

        # Get additional outputs to be included on the basis of the options, according to module type's own logic
        outputs = set(outputs) | set(cls.get_extra_outputs_from_options(options))

        return inputs, outputs, options

    def get_module_output_dir(self):
        return os.path.join(self.pipeline.short_term_store, self.module_name)

    def get_output_dir(self, output_name):
        return os.path.join(self.get_module_output_dir(), output_name)

    def get_output_datatype(self, output_name=None):
        if output_name is None:
            # Get the default output
            # Often there'll be only one output, so a name needn't be specified
            # If there are multiple, the first is the default
            output_name = self.default_output_name

        outputs = dict(self.available_outputs)
        if output_name not in outputs:
            raise PipelineStructureError("%s module does not have an output named '%s'. Available outputs: %s" %
                                         (self.module_type_name, output_name, ", ".join(self.output_names)))
        datatype = outputs[output_name]

        # The datatype might be a dynamic type -- a function that we call to get the type
        if type(datatype) is FunctionType:
            # Call the function to build the datatype
            datatype = datatype(self)
        return output_name, datatype

    def instantiate_output_datatype(self, output_name, output_datatype):
        """
        Subclasses may want to override this to provide special behaviour for instantiating
        particular outputs' datatypes.

        """
        return output_datatype(self.get_output_dir(output_name), self.pipeline)

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

    def get_input_datatype(self, input_name=None):
        """
        Get a datatype class corresponding to one of the inputs to the module.
        If an input name is not given, the first input is returned.

        """
        previous_module, output_name = self.get_input_module_connection(input_name)
        return previous_module.get_output_datatype(output_name)

    def get_input(self, input_name=None):
        """
        Get a datatype instance corresponding to one of the inputs to the module.
        Looks up the corresponding output from another module and uses that module's metadata to
        get that output's instance.
        If an input name is not given, the first input is returned.

        """
        previous_module, output_name = self.get_input_module_connection(input_name)
        return previous_module.get_output(output_name)

    def input_ready(self, input_name=None):
        previous_module, output_name = self.get_input_module_connection(input_name)
        if not previous_module.module_executable:
            # If the previous module isn't executable, this input is ready whenever all of its inputs are ready
            return all(previous_module.input_ready(previous_input) for previous_input in previous_module.input_names)
        else:
            # Otherwise, we just check whether the datatype is ready to go
            return previous_module.get_output(output_name).data_ready()

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
            input_type_requirements = module_inputs[input_name]
            # Input types may be tuples, to allow multiple types
            if type(input_type_requirements) is not tuple:
                input_type_requirements = (input_type_requirements,)
            # Load the dependent module
            dep_module = self.pipeline[dep_module_name]
            # Try to load the named output (or the default, if no name was given)
            output_name, dep_module_output = dep_module.get_output_datatype(output_name=output)
            # Check that the provided output type is a subclass of (or equal to) the required input type
            if not issubclass(dep_module_output, input_type_requirements):
                raise PipelineStructureError(
                    "module %s's %s-input is required to be of %s type (or a descendent), but module %s's "
                    "%s-output provides %s" % (
                        self.module_name, input_name, "/".join(t.__name__ for t in input_type_requirements),
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
    def __init__(self, module_instance_info):
        self.info = module_instance_info
        self.log = module_instance_info.pipeline.log

    def execute(self):
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
    def __init__(self, message, stderr=None, stdout=None):
        super(DependencyError, self).__init__(message)
        self.stdout = stdout
        self.stderr = stderr


def load_module_executor(path_or_info):
    """
    Utility for loading the executor class for a module from its full path.
    Just a wrapper around an import, with some error checking.

    :param path: path to Python package containing the module
    :return: class
    """
    if isinstance(path_or_info, basestring):
        # First import the metadata class
        module_info = load_module_info(path_or_info)
    else:
        module_info = path_or_info

    # Check this isn't an input module: they shouldn't be executed
    if not module_info.module_executable:
        raise ModuleExecutorLoadError("%s module type is not an executable module. It can't be (and doesn't need "
                                      "to be) executed: execute the next module in the pipeline" %
                                      module_info.module_type_name)
    # Check whether the module provides a special executor before trying to load one in the standard way
    if module_info.module_executor_override is not None:
        return module_info.module_executor_override
    else:
        if isinstance(path_or_info, basestring):
            executor_path = "%s.exec" % path_or_info

            try:
                mod = import_module(executor_path)
            except ImportError:
                raise ModuleInfoLoadError("module %s could not be loaded, could not import path %s" %
                                          (path_or_info, executor_path))
        else:
            # We were given a module info instance: work out where it lives and get the executor relatively
            try:
                mod = import_module("..exec", module_info.__module__)
            except ImportError:
                raise ModuleInfoLoadError("module %s could not be loaded, could not import ..exec from ModuleInfo's "
                                          "module, %s" %
                                          (path_or_info, module_info.__module__))
        if not hasattr(mod, "ModuleExecutor"):
            raise ModuleExecutorLoadError("could not load class %s.ModuleExecutor" % mod.__name__)
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
        raise ModuleInfoLoadError("module type '%s' could not be found (could not import %s)" % (path, info_path))

    if not hasattr(mod, "ModuleInfo"):
        raise ModuleInfoLoadError("invalid module type code: could not load class %s.ModuleInfo" % info_path)
    return mod.ModuleInfo
