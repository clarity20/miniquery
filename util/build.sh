#!/usr/bin/env bash

######## Helper functions ########

function make_clean() {
    # Move previous files to "old" directory
    echo Backing up older generated files ...
    mkdir -p "${BUILD_DIR}"
    for filename in "${CYTHON_CFG_FILE}"  "${GENERATED_CFILE}"  "${OBJECT_FILE}"  "${SHARED_LIBRARY}"; do
        mv "$filename" "${BUILD_DIR}"/old    # To suppress feedback: 2>/dev/null
    done
}

function generate_cython_config() {
    echo Generating cython cfg file ${CYTHON_CFG_FILE} ...
    for fn in "${SRC_DIR}"/*.py; do
      bn=`basename "$fn"`
      if [[ ! "$bn" =~ ^(setup|include)\.py$ ]]; then
        echo include \""$bn"\" >> "${CYTHON_CFG_FILE}"
      fi
    done
}

function generate_c_file() {
    echo Generating C file $GENERATED_CFILE ...
    "$CYTHON" -3 "${CYTHON_CFG_FILE}" -o "${GENERATED_CFILE}"
    ls -l "$GENERATED_CFILE"
}

######## Platform-agnostic definitions ########

PROJECT_DIR=${HOME}/projects/miniquery
SRC_DIR=${PROJECT_DIR}/util
BIN_DIR=${PROJECT_DIR}/bin

######## Main code ########

PYTHON="$( { which python3 || which python; } 2>/dev/null)" || { echo "ERROR: Python not found!"; exit 2; }
PYVERSION_DOT="$("$PYTHON" --version | sed -r 's/Python (.\..*)\..*/\1/')"
MACHINE_ARCH=`uname -m`

case $OSTYPE in
  *android*)

    CYTHON=cython
    BUILD_DIR=${SRC_DIR}/build/temp.linux-${MACHINE_ARCH}-${PYVERSION_DOT}
    CYTHON_CFG_FILE=${SRC_DIR}/utilIncludes.pyx
    GENERATED_CFILE=${BUILD_DIR}/utilIncludes.c
    OBJECT_FILE=${BUILD_DIR}/utilIncludes.o
    SHARED_LIBRARY=${BUILD_DIR}/utilIncludes.cpython-37m.so
    COMPILE=arm-linux-androideabi-clang

    make_clean
    generate_cython_config || exit 2
    generate_c_file || exit $?

    # Convert C source into .o object file
    echo Compiling to object file ...
    "$COMPILE" -mfpu=vfpv3-d16 -Wno-unused-result -Wsign-compare -DNDEBUG -g -fwrapv -O3 -Wall -march=armv7-a -mfpu=neon -mfloat-abi=softfp -mthumb -Os -I/data/data/com.termux/files/usr/include/python${PYVERSION_DOT}m -c "${GENERATED_CFILE}" -o "${OBJECT_FILE}" || exit 4

    # Generate DLL/.so from object file
    echo Creating shared object ...
    "$COMPILE" -shared -march=armv7-a -Wl,--fix-cortex-a8 -landroid-support -L/home/builder/.termux-build/_cache/android5-19b-arm-21-v3/sysroot/usr/lib "${OBJECT_FILE}" -L/data/data/com.termux/files/usr/lib -lpython${PYVERSION_DOT}m -o "${SHARED_LIBRARY}" || exit 5

    strip "${SHARED_LIBRARY}" || exit 6
    echo Finished.
    ;;

  *linux*)

    CYTHON=cython
    BUILD_DIR=${SRC_DIR}/build/temp.linux-${MACHINE_ARCH}-${PYVERSION_DOT}m
    CYTHON_CFG_FILE=${SRC_DIR}/utilIncludes.pyx
    GENERATED_CFILE=${BUILD_DIR}/utilIncludes.c
    OBJECT_FILE=${BUILD_DIR}/utilIncludes.o
    SHARED_LIBRARY=${BUILD_DIR}/utilIncludes.so
    COMPILE=gcc

    make_clean
    generate_cython_config || exit 2
    generate_c_file || exit $?

    echo Compiling to object file ...
    "$COMPILE" -pthread -fno-strict-aliasing -DNDEBUG -O2 -g -pipe -Wall -Werror=format-security -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -specs=/usr/lib/rpm/redhat/redhat-hardened-cc1 -m64 -mtune=generic -D_GNU_SOURCE -fPIC -fwrapv -I/usr/include/python${PYVERSION_DOT}m -c "${GENERATED_CFILE}" -o "${OBJECT_FILE}" || exit 4

    echo Creating shared object ...
    "$COMPILE" -pthread -shared -Wl,-z,relro -specs=/usr/lib/rpm/redhat/redhat-hardened-ld "${OBJECT_FILE}" -L/usr/lib64 -lpython${PYVERSION_DOT}m -o "${SHARED_LIBRARY}" || exit 5

    strip "${SHARED_LIBRARY}" || exit 6
    ;;

  *)
    # For Windows. Any other OS'es should be added before this section.
    USAGE="USAGE: $0 buildType\n    buildTypes:  x86  x86_64"
    BUILDTYPE="$1"
    if [[ -z "$BUILDTYPE" ]]; then
        echo -e "$USAGE"
        exit 1
    fi

    PYVERSION="${PYVERSION_DOT/./}"
    case $BUILDTYPE in
        [Xx]86_64)
            TARGET_ARCH=x64
            ;;
        [Xx]86)
            TARGET_ARCH=x86
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
    CYTHON="$PYTHONDIR"/Scripts/cython.exe

    BUILD_DIR=${SRC_DIR}/build/temp.win32-${PYVERSION_DOT}/Release  # derived from cythonize
    CYTHON_CFG_FILE=${SRC_DIR}/utilIncludes.pyx      # same dir as source files
    GENERATED_CFILE=${BUILD_DIR}/utilIncludes.c
    OBJECT_FILE=${BUILD_DIR}/utilIncludes${TARGET_ARCH:1}.obj
    SHARED_LIBRARY=${BUILD_DIR}/utilIncludes${TARGET_ARCH:1}.pyd

    make_clean
    generate_cython_config || exit 2
    generate_c_file || exit $?

    # Prepare for compilation using windows-style pathnames
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
    LINK=${MSTOOLS}/link.exe

    PYTHONDIR="$(cygpath -w "$PYTHONDIR")"

    # Compile.
    "$COMPILE" -c -I"$PYTHONDIR\\include" -I"$WINKIT_INC\\ucrt" -I"$MSVC\\include" \
        -I"$WINKIT_INC\\shared" "$GENERATED_CFILE" -Fo: "$OBJECT_FILE"

    # Link.
    "$LINK" -DLL -OUT:"$SHARED_LIBRARY" "$OBJECT_FILE" "$PYTHONDIR\\libs\\python${PYVERSION}.lib" \
        "$MSVC_LIBS\\libcmt.lib" "$MSVC_LIBS\\oldnames.lib" "$UMDIR\\kernel32.lib" \
        "$MSVC_LIBS\\libvcruntime.lib" "$UCRTDIR\\libucrt.lib" "$UMDIR\\Uuid.lib"

    # Populate "bin" with the product-ready file
    mkdir -p "$BIN_DIR"
    cp "$SHARED_LIBRARY" "$BIN_DIR"/utilIncludes.pyd

    ;;

esac
