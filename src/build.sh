#!/usr/bin/env bash

######## Helper functions ########

ERRCODE_MV_FAILED=100
function make_clean() {
    # Move previous files to "old" directory
    if ! mv "${INCLUDES_PYX}"  "${INCLUDES_C}"  "${INCLUDES_O}"  "${INCLUDES_SO}" old 2>/dev/null; then
        echo WARNING: File backups failed. 2> /dev/null
        return $ERRCODE_MV_FAILED
    fi
}

function generate_includes_pyx() {
    for fn in "${SRC_DIR}"/*.py; do
      bn=`basename "$fn"`
      if [[ ! "$bn" =~ ^(setup|include)\.py$ ]]; then
        echo include \""$bn"\" >> "${INCLUDES_PYX}"
      fi
    done
}

function includes_pyx_to_c() {
    cython -3 "${INCLUDES_PYX}"
}

######## Platform-agnostic definitions ########

PROJECT_DIR=${HOME}/projects/miniquery
SRC_DIR=${PROJECT_DIR}/src
INCLUDES_PYX=${SRC_DIR}/includes.pyx
INCLUDES_C=${SRC_DIR}/includes.c

######## Main code ########

case $OSTYPE in
  *android*)

    CYTHON=cython
    STDERR=/proc/self/fd/2
    BUILD_DIR=${SRC_DIR}/build/temp.linux-armv7l-3.7
    INCLUDES_O=${BUILD_DIR}/includes.o
    INCLUDES_SO=${SRC_DIR}/includes.cpython-37m.so
    COMPILE=arm-linux-androideabi-clang

    make_clean
    generate_includes_pyx || exit 2
    includes_pyx_to_c || exit 3

    # Convert C source into .o object file
    "$COMPILE" -mfloat-abi=softfp -mfpu=vfpv3-d16 -Wno-unused-result -Wsign-compare -DNDEBUG -g -fwrapv -O3 -Wall -march=armv7-a -mfpu=neon -mfloat-abi=softfp -mthumb -Os -march=armv7-a -mfpu=neon -mfloat-abi=softfp -mthumb -Os -fPIC -I/data/data/com.termux/files/usr/include/python3.7m -c "${INCLUDES_C}" -o "${INCLUDES_O}" || exit 4

    # Generate DLL/.so from object file
    "$COMPILE" -shared -L/data/data/com.termux/files/usr/lib -march=armv7-a -landroid-support -L/home/builder/.termux-build/_cache/android5-19b-arm-21-v3/sysroot/usr/lib -march=armv7-a -Wl,--fix-cortex-a8 -L/data/data/com.termux/files/usr/lib -march=armv7-a -landroid-support -L/home/builder/.termux-build/_cache/android5-19b-arm-21-v3/sysroot/usr/lib "${INCLUDES_O}" -L/data/data/com.termux/files/usr/lib -lpython3.7m -o "${INCLUDES_SO}" || exit 5

    strip "${INCLUDES_SO}" || exit 6
    ;;

  *linux*)

    CYTHON=cython
    STDERR=/dev/stderr
    BUILD_DIR=${SRC_DIR}/build/temp.linux-x86_64-3.4m
    INCLUDES_O=${BUILD_DIR}/includes.o
    INCLUDES_SO=${SRC_DIR}/includes.so
    COMPILE=gcc

    make_clean || echo "WARNING: File backups failed." > "$STDERR"
    generate_includes_pyx ||exit 2
    includes_pyx_to_c || exit 3

    "$COMPILE" -pthread -fno-strict-aliasing -O2 -DNDEBUG -O2 -g -pipe -Wall -Werror=format-security -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -specs=/usr/lib/rpm/redhat/redhat-hardened-cc1 -m64 -mtune=generic -D_GNU_SOURCE -fPIC -fwrapv -fPIC -I/usr/include/python3.4m -c "${INCLUDES_C}" -o "${INCLUDES_O}" || exit 4
    "$COMPILE" -pthread -shared -Wl,-z,relro -specs=/usr/lib/rpm/redhat/redhat-hardened-ld "${INCLUDES_O}" -L/usr/lib64 -lpython3.4m -o "${INCLUDES_SO}" || exit 5

    strip "${INCLUDES_SO}" || exit 6
    ;;

  *)
    # For Windows. Any other OS'es should be added before this section.
    USAGE="USAGE: $0 buildType"$'\n'"    buildTypes:  x86  x86_64"
    BUILDTYPE="$1"
    if [[ -z "$BUILDTYPE" ]]; then
        echo "$USAGE"
	exit 1
    fi

    PYVERSION="$(python --version)"
    PYVERSION="$(echo "$PYVERSION" | sed -r 's/Python (.)\.(.*)\..*/\1\2/')"
    case $BUILDTYPE in
        [Xx]86_64)
            PYTHONDIR=Python$PYVERSION
            ARCH=x64
            ;;
        [Xx]86)
            PYTHONDIR=Python${PYVERSION}-32
            ARCH=x86
            ;;
        *)
            echo "$USAGE"
            exit 1
            ;;
    esac

    PYTHONDIR="$HOME/AppData/Local/Programs/Python/$PYTHONDIR/"
    CYTHONDIR="$PYTHONDIR/Scripts/"
    CYTHON=$CYTHONDIR/cython.exe
    STDERR=/dev/stderr
    BUILD_DIR=${SRC_DIR}/build/${ARCH}
    INCLUDES_O=${BUILD_DIR}/includes.obj      # $ARCH-dependent; place accordingly
    INCLUDES_SO=${BUILD_DIR}/includes.dll     # $ARCH-dependent; place accordingly

    make_clean
    generate_includes_pyx || exit 2
    includes_pyx_to_c || exit $?

    PF="C:\\Program Files (x86)"
    MSVC="${PF}\\Microsoft Visual Studio\\2019\\BuildTools\\VC\\Tools\MSVC\\14.24.28314"
    MSVC_LIBS="${MSVC}\\lib\\${ARCH}"
    WIN_KITS="${PF}\\Windows Kits\\10\\Lib\\10.0.18362.0"
    UCRTDIR="${WIN_KITS}\\ucrt\\$ARCH"
    UMDIR="${WIN_KITS}\\um\\$ARCH"
    MSTOOLS=${MSVC}/bin/HostX64/${ARCH}
    COMPILE=${MSTOOLS}/cl.exe
    LINK=${MSTOOLS}/link.exe

    PYTHONDIR="$(cygpath -w "$PYTHONDIR")"

    # Compile. ('/' syntax does not work at the bash prompt, so use '-'.)
    "$COMPILE" -c -I"$PYTHONDIR\\include" -I"$WIN_KITS\\ucrt" -I"$MSVC\\include" \
        -I"$WIN_KITS\\shared" "$INCLUDES_C" -Fo: "$INCLUDES_O"

    # Link. (-LD creates a dll.)
    "$LINK" -DLL -OUT:"$INCLUDES_SO" "$INCLUDES_O" "$PYTHONDIR\\libs\\python${PYVERSION}.lib" \
        "$MSVC_LIBS\\libcmt.lib" "$MSVC_LIBS\\oldnames.lib" "$UMDIR\\kernel32.lib" \
        "$MSVC_LIBS\\libvcruntime.lib" "$UCRTDIR\\libucrt.lib" "$UMDIR\\Uuid.lib"
    ;;
esac
