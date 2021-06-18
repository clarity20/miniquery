#!/usr/bin/env bash

######## Helper functions ########

function make_clean() {
    # Move previous files to "old" directory
    for filename in "${CYTHON_CFG_FILE}"  "${GENERATED_CFILE}"  "${OBJECT_FILE}"  "${SHARED_LIBRARY}"; do
        mv "$filename" "${BUILD_DIR}"/old    # To suppress feedback:m 2>/dev/null
    done
}

function generate_cython_config() {
    for fn in "${SRC_DIR}"/*.py; do
      bn=`basename "$fn"`
      if [[ ! "$bn" =~ ^(setup|include)\.py$ ]]; then
        echo include \""$bn"\" >> "${CYTHON_CFG_FILE}"
      fi
    done
}

function generate_c_file() {
    sed -i -e 's/miniGlobals /utilIncludes /' ${SRC_DIR}/argumentClassifier.py
    cython -3 "${CYTHON_CFG_FILE}" -o "${GENERATED_CFILE}"
    sed -i -e 's/utilIncludes /miniGlobals /' ${SRC_DIR}/argumentClassifier.py
}

######## Platform-agnostic definitions ########

PROJECT_DIR=${HOME}/projects/miniquery
SRC_DIR=${PROJECT_DIR}/src
BIN_DIR=${PROJECT_DIR}/bin

######## Main code ########

case $OSTYPE in
  *android*)

    CYTHON=cython
    BUILD_DIR=${SRC_DIR}/build/temp.linux-armv7l-3.7
    CYTHON_CFG_FILE=${SRC_DIR}/includes.pyx
    GENERATED_CFILE=${SRC_DIR}/includes.c
    OBJECT_FILE=${BUILD_DIR}/includes.o
    SHARED_LIBRARY=${SRC_DIR}/includes.cpython-37m.so
    COMPILE=arm-linux-androideabi-clang

    make_clean
    generate_cython_config || exit 2
    generate_c_file || exit 3

    # Convert C source into .o object file
    "$COMPILE" -mfloat-abi=softfp -mfpu=vfpv3-d16 -Wno-unused-result -Wsign-compare -DNDEBUG -g -fwrapv -O3 -Wall -march=armv7-a -mfpu=neon -mfloat-abi=softfp -mthumb -Os -march=armv7-a -mfpu=neon -mfloat-abi=softfp -mthumb -Os -fPIC -I/data/data/com.termux/files/usr/include/python3.7m -c "${GENERATED_CFILE}" -o "${OBJECT_FILE}" || exit 4

    # Generate DLL/.so from object file
    "$COMPILE" -shared -L/data/data/com.termux/files/usr/lib -march=armv7-a -landroid-support -L/home/builder/.termux-build/_cache/android5-19b-arm-21-v3/sysroot/usr/lib -march=armv7-a -Wl,--fix-cortex-a8 -L/data/data/com.termux/files/usr/lib -march=armv7-a -landroid-support -L/home/builder/.termux-build/_cache/android5-19b-arm-21-v3/sysroot/usr/lib "${OBJECT_FILE}" -L/data/data/com.termux/files/usr/lib -lpython3.7m -o "${SHARED_LIBRARY}" || exit 5

    strip "${SHARED_LIBRARY}" || exit 6
    ;;

  *linux*)

    CYTHON=cython
    BUILD_DIR=${SRC_DIR}/build/temp.linux-x86_64-3.4m
    CYTHON_CFG_FILE=${SRC_DIR}/includes.pyx
    GENERATED_CFILE=${SRC_DIR}/includes.c
    OBJECT_FILE=${BUILD_DIR}/includes.o
    SHARED_LIBRARY=${SRC_DIR}/includes.so
    COMPILE=gcc

    make_clean
    generate_cython_config || exit 2
    generate_c_file || exit 3

    "$COMPILE" -pthread -fno-strict-aliasing -O2 -DNDEBUG -O2 -g -pipe -Wall -Werror=format-security -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -specs=/usr/lib/rpm/redhat/redhat-hardened-cc1 -m64 -mtune=generic -D_GNU_SOURCE -fPIC -fwrapv -fPIC -I/usr/include/python3.4m -c "${GENERATED_CFILE}" -o "${OBJECT_FILE}" || exit 4
    "$COMPILE" -pthread -shared -Wl,-z,relro -specs=/usr/lib/rpm/redhat/redhat-hardened-ld "${OBJECT_FILE}" -L/usr/lib64 -lpython3.4m -o "${SHARED_LIBRARY}" || exit 5

    strip "${SHARED_LIBRARY}" || exit 6
    ;;

  *)
    # For Windows. Any other OS'es should be added before this section.
    USAGE="USAGE: $0 buildType"$'\n'"    buildTypes:  x86  x86_64"
    BUILDTYPE="$1"
    if [[ -z "$BUILDTYPE" ]]; then
        echo "$USAGE"
	exit 1
    fi

    PYTHON="$( { which python3 || which python; } 2>/dev/null)" || { echo "ERROR! Python not found!"; exit 2; }
    PYVERSION_DOT="$("$PYTHON" --version | sed -r 's/Python (.\..*)\..*/\1/')"
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
    CYTHON_CFG_FILE=${SRC_DIR}/includes.pyx
    GENERATED_CFILE=${BUILD_DIR}/includes.c
    OBJECT_FILE=${BUILD_DIR}/includes${TARGET_ARCH:1}.obj
    SHARED_LIBRARY=${BUILD_DIR}/includes${TARGET_ARCH:1}.pyd

    make_clean
    generate_cython_config || exit 2
    generate_c_file || exit $?

    # Prepare for compilation using windows-style pathnames
    PF="C:\\Program Files (x86)"
    MSVC="${PF}\\Microsoft Visual Studio\\2019\\BuildTools\\VC\\Tools\MSVC\\14.24.28314"
    MSVC_LIBS="${MSVC}\\lib\\${TARGET_ARCH}"
    WINKIT_INC="${PF}\\Windows Kits\\10\\Include\\10.0.18362.0"  # Windows Kits are downloaded from Microsoft
    WINKIT_LIBS="${PF}\\Windows Kits\\10\\Lib\\10.0.18362.0"
    UCRTDIR="${WINKIT_LIBS}\\ucrt\\$TARGET_ARCH"
    UMDIR="${WINKIT_LIBS}\\um\\$TARGET_ARCH"
    MSTOOLS=${MSVC}/bin/Host${HOST_ARCH}/${TARGET_ARCH}
    COMPILE=${MSTOOLS}/cl.exe
    LINK=${MSTOOLS}/link.exe

    PYTHONDIR="$(cygpath -w "$PYTHONDIR")"

    # Compile. ('/' syntax does not work at the bash prompt, so use '-'.)
    "$COMPILE" -c -I"$PYTHONDIR\\include" -I"$WINKIT_INC\\ucrt" -I"$MSVC\\include" \
        -I"$WINKIT_INC\\shared" "$GENERATED_CFILE" -Fo: "$OBJECT_FILE"

    # Link. (-LD creates a dll.)
    "$LINK" -DLL -OUT:"$SHARED_LIBRARY" "$OBJECT_FILE" "$PYTHONDIR\\libs\\python${PYVERSION}.lib" \
        "$MSVC_LIBS\\libcmt.lib" "$MSVC_LIBS\\oldnames.lib" "$UMDIR\\kernel32.lib" \
        "$MSVC_LIBS\\libvcruntime.lib" "$UCRTDIR\\libucrt.lib" "$UMDIR\\Uuid.lib"

    # Populate "bin" with the product-ready file
    mkdir -p "$BIN_DIR"
    cp "$SHARED_LIBRARY" "$BIN_DIR"/includes.pyd
    ;;
esac
