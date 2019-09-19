######## Helper functions ########

function make_clean() {
    # Move previous files to "old" directory
    mv "${INCLUDES_PYX}"  "${INCLUDES_C}"  "${INCLUDES_O}"  "${INCLUDES_SO}" old
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
SRC_DIR=${PROJECT_DIR}/util
INCLUDES_PYX=${SRC_DIR}/utilIncludes.pyx
INCLUDES_C=${SRC_DIR}/utilIncludes.c

######## Main code ########

case $OSTYPE in
  *android*)

    STDERR=/proc/self/fd/2
    BUILD_DIR=${SRC_DIR}/build/temp.linux-armv7l-3.7
    INCLUDES_O=${BUILD_DIR}/utilIncludes.o
    INCLUDES_SO=${SRC_DIR}/utilIncludes.cpython-37m.so

    make_clean || echo "WARNING: File backups failed." > "$STDERR"
    generate_includes_pyx || exit 2
    includes_pyx_to_c || exit 3

    # Convert C source into .o object file
    arm-linux-androideabi-clang -mfloat-abi=softfp -mfpu=vfpv3-d16 -Wno-unused-result -Wsign-compare -DNDEBUG -g -fwrapv -O3 -Wall -march=armv7-a -mfpu=neon -mfloat-abi=softfp -mthumb -Os -march=armv7-a -mfpu=neon -mfloat-abi=softfp -mthumb -Os -fPIC -I/data/data/com.termux/files/usr/include/python3.7m -c "${INCLUDES_C}" -o "${INCLUDES_O}" || exit 4

    # Generate DLL/.so from object file
    arm-linux-androideabi-clang -shared -L/data/data/com.termux/files/usr/lib -march=armv7-a -landroid-support -L/home/builder/.termux-build/_cache/android5-19b-arm-21-v3/sysroot/usr/lib -march=armv7-a -Wl,--fix-cortex-a8 -L/data/data/com.termux/files/usr/lib -march=armv7-a -landroid-support -L/home/builder/.termux-build/_cache/android5-19b-arm-21-v3/sysroot/usr/lib "${INCLUDES_O}" -L/data/data/com.termux/files/usr/lib -lpython3.7m -o "${INCLUDES_SO}" || exit 5

    strip "${INCLUDES_SO}" || exit 6
    ;;

  *linux*)

    STDERR=/dev/stderr
    BUILD_DIR=${SRC_DIR}/build/temp.linux-x86_64-3.4m
    INCLUDES_O=${BUILD_DIR}/utilIncludes.o
    INCLUDES_SO=${SRC_DIR}/utilIncludes.so

    make_clean || echo "WARNING: File backups failed." > "$STDERR"
    generate_includes_pyx ||exit 2
    includes_pyx_to_c || exit 3

    gcc -pthread -fno-strict-aliasing -O2 -DNDEBUG -O2 -g -pipe -Wall -Werror=format-security -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -specs=/usr/lib/rpm/redhat/redhat-hardened-cc1 -m64 -mtune=generic -D_GNU_SOURCE -fPIC -fwrapv -fPIC -I/usr/include/python3.4m -c "${INCLUDES_C}" -o "${INCLUDES_O}" || exit 4
    gcc -pthread -shared -Wl,-z,relro -specs=/usr/lib/rpm/redhat/redhat-hardened-ld "${INCLUDES_O}" -L/usr/lib64 -lpython3.4m -o "${INCLUDES_SO}" || exit 5

    strip "${INCLUDES_SO}" || exit 6
    ;;

  *win*)
    STDERR=/dev/stderr
    echo "Windows not implemented." > "$STDERR"
    ;;
esac
