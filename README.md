# CJake

## Installation

All of these steps were reproduced only on the Ubuntu 18.04 installation.

### Requirements

- python 3 environment
- Doxygen
- XSLTproc

### Installation steps

- Clone OpenJDK 8 sources from its mercurial repository.
- Set the source paths for `JDK scripts/generate_jvm_headers.sh` and execute it to generate headers used by JVM.
- Generate/download Java Standard Library classfiles (Download is preferable).
- From the directory with Standard Library class file run `JDK scripts/generate_jvm_headers.sh` which will generate JNI headers.
- Copy newly generated `.h` files to the `/generated/lang_headers`
- Generate headers containing only macros using `python generate_macro_only_headers.py`

### Usage

Run `python analisys_tool.py`

#### Output format

- File usage. It lists all files that were included by target files and show the number of dependent files as well as their paths. Example:

```
'oops/typeArrayKlass.hpp' used by 2 : ['prims/jni.h', 'jni.h']
```

- Functions report. It lists all structures (not only functions) that were involved sorted by modules. Example:

```Module 'classfile/classLoader.hpp', filepath '../jdk8/hotspot/src/share/vm/classfile/classLoader.hpp'
    PerfClassTraceTime,
    compile_the_world_in,
    initialize,
    name,
```

### Options

The only way to configure options for now is editing variables in the script

- `PROCESS_FILES` - Process files specified in the target_files.json
- `PROCESS_DIRS` - Process directories specified in the target_files.json

Formatting varaibles

- `PRINT_ALL` - Print all dependencies in file usage.
- `USAGE_VIEW` - Target files and modules that they are using if True, prints used modules and by which modules they are used.

Processing options

- `ONLY_C_STYLE` - Process only functions and variables.
- `PROCESS_ALTERNATIVES` - Process all names including classes, methods, fields and others.

Logging

- `LOG_TO_STDOUT` - Print logs to STDOUT if True and save to file in the same directory, otherwise.
- `LOG_NAME_FORMAT` - Format of the name of a log file. Can include date and time using datetime strftime formatting `CJake log %H-%M-%S %d-%m-%Y.log`.
- `LOG_LEVEL` - Level of messages displayed in logs. Should be set to one of default python logging module levels.
