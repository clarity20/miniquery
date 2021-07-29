#!/usr/bin/env bash

######## Helper functions ########

function make_clean()
{
    # Move previous files to "old" directory
    for filename in "${GENERATED_CFILE}" "${EXECUTABLE}" ; do
        mv "$filename" "${BUILD_DIR}"/old     # To suppress feedback: 2>/dev/null
    done
}

function generate_c_file()
{
    SOURCE_CONVERSION_SCRIPT=${SRC_DIR}/tempMiniForBuild.sh
    TEMP_SOURCE_FILE=${SRC_DIR}/mini_edited_for_build.py

    "${SOURCE_CONVERSION_SCRIPT}" "${SOURCE_FILE}" > "${TEMP_SOURCE_FILE}" || { echo "build.sh ERROR: mini.py conversion failed."; exit 3; }
    "$CYTHON" -3 --embed "${TEMP_SOURCE_FILE}" -o "${GENERATED_CFILE}"
    rm -f "${TEMP_SOURCE_FILE}"
}

######## Platform-agnostic definitions ########

PROJECT_DIR=${HOME}/projects/miniquery
SRC_DIR=${PROJECT_DIR}/scripts
BIN_DIR=${PROJECT_DIR}/bin
SOURCE_FILE=${SRC_DIR}/mini.py

######## Main code ########

PYTHON="$( { which python3 || which python; } 2>/dev/null)" || { echo "ERROR: Python not found!"; exit 2; }
PYVERSION_DOT="$("$PYTHON" --version | sed -r 's/Python (.\..*)\..*/\1/')"

case $OSTYPE in
  *android*)

    CYTHON=cython
    BUILD_DIR=${SRC_DIR}/build
    GENERATED_CFILE=${BUILD_DIR}/mini.c
    EXECUTABLE=${BUILD_DIR}/mini

    make_clean
    generate_c_file || exit 2

    COMPILE=arm-linux-androideabi-clang

    # Generate EXE from C source file
    "$COMPILE" -I /data/data/com.termux/files/usr/include/python${PYVERSION_DOT}m -L /data/data/com.termux/files/usr/lib -o "${EXECUTABLE}" "${GENERATED_CFILE}" -lpython${PYVERSION_DOT}m || exit 3

    strip "${EXECUTABLE}" || exit 4
    ;;

  *linux*)

    CYTHON=cython
    BUILD_DIR=${SRC_DIR}/build
    GENERATED_CFILE=${BUILD_DIR}/mini.c
    EXECUTABLE=${BUILD_DIR}/mini

    make_clean
    generate_c_file || exit 2

    COMPILE=gcc

    "$COMPILE" -I /usr/include/python${PYVERSION_DOT}m -L /usr/lib64 -o "${EXECUTABLE}" "${GENERATED_CFILE}" -lpython${PYVERSION_DOT}m || exit 3

    strip "${EXECUTABLE}" || exit 4
    ;;

  *)
    # For Windows. Any other OS'es should be added before this section.
    USAGE="USAGE: $0 targetArch\n    targetArch:  x86  or  x86_64"
    BUILDTYPE="$1"
    if [[ -z "$BUILDTYPE" ]]; then
        echo -e "$USAGE"
        exit 1
    fi

    PYVERSION=${PYVERSION_DOT/./}
    case $BUILDTYPE in
        [Xx]86_64)
            TARGET_ARCH=x64
	    ;;
        [Xx]86)
            TARGET_ARCH=x32
	    ;;
        *)
        echo "$USAGE"
        exit 1
        ;;
    esac

    HOST_ARCH="$(uname -m)"
    if [[ "$HOST_ARCH" =~ _64$ ]]; then
        HOST_ARCH=x64
    else
        HOST_ARCH=x86
    fi

    PYTHONDIR=$(dirname "$PYTHON")
    PYTHONDLL="$PYTHONDIR"/python${PYVERSION}.dll   # version-sensitive but not wordsize-sensitive
    CYTHON=$PYTHONDIR/Scripts/cython.exe

    # Squirrel away the generated files in a build directory
    BUILD_DIR=${SRC_DIR}/build/temp.win32-${PYVERSION_DOT}/Release   # this name was chosen by cythonize
    GENERATED_CFILE=${BUILD_DIR}/mini.c
    EXECUTABLE=${BUILD_DIR}/mini${TARGET_ARCH:1}.exe    # indicate word size in the name
    OBJECT_FILE=${EXECUTABLE/%exe/obj}     # store OBJ alongside EXE

    make_clean
    generate_c_file || exit 2

    # Prepare for compilation. Use windows-style pathnames.
    PF="C:\\Program Files (x86)"
    MSVC="${PF}\\Microsoft Visual Studio\\2019\\BuildTools\\VC\\Tools\\MSVC\\14.24.28314"
    MSVC_LIBS="${MSVC}\\lib\\${TARGET_ARCH}"
    WINKIT_HOME="${PF}\\Windows Kits\\10"  # Windows Kits are downloaded from Microsoft
    WINKIT_MANIFEST="$(cygpath "${WINKIT_HOME}")"/SDKManifest.xml
    WINKIT_VERSION=$(sed -rn '/Platform/ s/.*Version=([0-9.]+)"/\1/p' "$WINKIT_MANIFEST")
    WINKIT_INC="${WINKIT_HOME}\\Include\\${WINKIT_VERSION}"
    WINKIT_LIBS="${WINKIT_HOME}\\Lib\\${WINKIT_VERSION}"
    UCRTDIR="${WINKIT_LIBS}\\ucrt\\$TARGET_ARCH"
    UMDIR="${WINKIT_LIBS}\\um\\$TARGET_ARCH"
    MSTOOLS=${MSVC}/bin/Host${HOST_ARCH}/${TARGET_ARCH}
    COMPILE=${MSTOOLS}/cl.exe

    PYTHONDIR=$(cygpath -w "$PYTHONDIR")

    # Compilation: Use naming conventions the compiler understands
    "$COMPILE" -I"$PYTHONDIR\\include" -I"$WINKIT_INC\\ucrt" -I"$MSVC\\include" \
        -I"$WINKIT_INC\\shared" "${GENERATED_CFILE}" -Fo: "${OBJECT_FILE}" -Fe: "${EXECUTABLE}" -link \
        "$PYTHONDIR\\libs\\python${PYVERSION}.lib" "$MSVC_LIBS\\libcmt.lib" \
        "$MSVC_LIBS\\oldnames.lib" "$UMDIR\\kernel32.lib" "$MSVC_LIBS\\libvcruntime.lib" \
        "$UCRTDIR\\libucrt.lib" "$UMDIR\\Uuid.lib"

    # Populate "bin" with the product-ready files
    mkdir -p "$BIN_DIR"
    cp "$EXECUTABLE" "$BIN_DIR"/mini.exe
    cp "$PYTHONDLL" "$BIN_DIR"

    ;;
esac
