######## Helper functions ########

function make_clean()
{
    # Move previous files to "old" directory
    if ! mv "${MINI_C}" "${MINI_EXE}" old 2>/dev/null; then
        echo WARNING: File backups failed. 2> /dev/null
        return 1
    fi
}

function generate_mini_c()
{
    "$CYTHON" -3 --embed "${MINI_PY}" -o "${MINI_C}"
}

######## Platform-agnostic definitions ########

PROJECT_DIR=${HOME}/projects/miniquery
SCRIPT_DIR=${PROJECT_DIR}/scripts
MINI_PY=${SCRIPT_DIR}/mini.py
MINI_C=${SCRIPT_DIR}/mini.c

######## Main code ########

case $OSTYPE in
  *android*)

    CYTHON=cython
    BUILD_DIR=${SCRIPT_DIR}
    MINI_EXE=${BUILD_DIR}/mini

    make_clean
    generate_mini_c || exit 2

    COMPILE=arm-linux-androideabi-clang

    # Generate EXE from C source file
    "$COMPILE" -I /data/data/com.termux/files/usr/include/python3.7m -L /data/data/com.termux/files/usr/lib -o "${MINI_EXE}" "${MINI_C}" -lpython3.7m || exit 3

    strip "${MINI_EXE}" || exit 4
    ;;

  *linux*)

    CYTHON=cython
    BUILD_DIR=${SCRIPT_DIR}
    MINI_EXE=${BUILD_DIR}/mini

    make_clean
    generate_mini_c || exit 2

    COMPILE=gcc

    "$COMPILE" -I /usr/include/python3.4m -L /usr/lib64 -o "${MINI_EXE}" "${MINI_C}" -lpython3.4m || exit 3

    strip "${MINI_EXE}" || exit 4
    ;;

  *)
    # For Windows. Any other OS'es should be added before this section.
    USAGE="USAGE: $0 targetArch\n    targetArch:  x86  or  x86_64"
    BUILDTYPE="$1"
    if [[ -z "$BUILDTYPE" ]]; then
        echo -e "$USAGE"
        exit 1
    fi

    PYTHON="$( { which python3 || which python; } 2>/dev/null)" || { echo "ERROR: Python not found!"; exit 2; }
    PYVERSION_DOT="$("$PYTHON" --version | sed -r 's/Python (.\..*)\..*/\1/')"
    PYVERSION=${PYVERSION_DOT/./}
    case $BUILDTYPE in
        [Xx]86_64)
            PYTHONDIR=Python$PYVERSION
            TARGET_ARCH=x64
	    ;;
        [Xx]86)
            PYTHONDIR=Python${PYVERSION}-32
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
    CYTHON=$PYTHONDIR/Scripts/cython.exe

    # Squirrel away the generated files in a build directory
    BUILD_DIR=${SCRIPT_DIR}/build/temp.win32-${PYVERSION_DOT}/Release   # this name was set by cythonize
    MINI_C=${BUILD_DIR}/mini.c
    MINI_EXE=${BUILD_DIR}/mini${TARGET_ARCH:1}.exe    # force the name to contain either 32 or 64
    MINI_OBJ=${MINI_EXE/%exe/obj}     # store OBJ alongside EXE

    make_clean
    generate_mini_c || exit 2

    PF="C:\\Program Files (x86)"
    MSVC="${PF}\\Microsoft Visual Studio\\2019\\BuildTools\\VC\\Tools\\MSVC\\14.24.28314"
    MSVC_LIBS="${MSVC}\\lib\\${TARGET_ARCH}"
    WINKIT_INC="${PF}\\Windows Kits\\10\\Include\\10.0.18362.0"  # Windows kits are downloaded from Microsoft
    WINKIT_LIBS="${PF}\\Windows Kits\\10\\Lib\\10.0.18362.0"
    UCRTDIR="${WINKIT_LIBS}\\ucrt\\$TARGET_ARCH"
    UMDIR="${WINKIT_LIBS}\\um\\$TARGET_ARCH"
    MSTOOLS=${MSVC}/bin/Host${HOST_ARCH}/${TARGET_ARCH}
    COMPILE=${MSTOOLS}/cl.exe

    PYTHONDIR=$(cygpath -w "$PYTHONDIR")

    # Compilation: Use naming conventions the compiler understands
    "$COMPILE" -I"$PYTHONDIR\\include" -I"$WINKIT_INC\\ucrt" -I"$MSVC\\include" \
        -I"$WINKIT_INC\\shared" "${MINI_C}" -Fo: "${MINI_OBJ}" -Fe: "${MINI_EXE}" -link \
	"$PYTHONDIR\\libs\\python${PYVERSION}.lib" "$MSVC_LIBS\\libcmt.lib" \
	"$MSVC_LIBS\\oldnames.lib" "$UMDIR\\kernel32.lib" "$MSVC_LIBS\\libvcruntime.lib" \
	"$UCRTDIR\\libucrt.lib" "$UMDIR\\Uuid.lib"

    # Move the essential built files to the top of this subtree.
    cp "${MINI_EXE}" "${SOURCE_DIR}"/mini.exe

    ;;
esac
