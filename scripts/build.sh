######## Helper functions ########

function make_clean()
{
    # Move previous files to "old" directory
    mv "${MINI_C}" "${MINI_EXE}" old
}

function generate_mini_c()
{
    cython -3 --embed "${MINI_PY}"
}

######## Platform-agnostic definitions ########

PROJECT_DIR=${HOME}/projects/miniquery
SCRIPT_DIR=${PROJECT_DIR}/scripts
MINI_PY=${SCRIPT_DIR}/mini.py
MINI_C=${SCRIPT_DIR}/mini.c

######## Main code ########

case $OSTYPE in
  *android*)

    STDERR=/proc/self/fd/2
    MINI_EXE=${SCRIPT_DIR}/mini

    make_clean || echo "WARNING: File backups failed." > "$STDERR"
    generate_mini_c || exit 2

    # Generate EXE from C source file
    arm-linux-androideabi-clang -I /data/data/com.termux/files/usr/include/python3.7m -L /data/data/com.termux/files/usr/lib -o "${MINI_EXE}" "${MINI_C}" -lpython3.7m || exit 3

    strip "${MINI_EXE}" || exit 4
    ;;

  *linux*)

    STDERR=/dev/stderr
    MINI_EXE=${SCRIPT_DIR}/mini

    make_clean || echo "WARNING: File backups failed." > "$STDERR"
    generate_mini_c || exit 2

    gcc -I /usr/include/python3.4m -L /usr/lib64 -o "${MINI_EXE}" "${MINI_C}" -lpython3.4m || exit 3

    strip "${MINI_EXE}" || exit 4
    ;;

  *win*)
    STDERR=/dev/stderr
    MINI_EXE=${SCRIPT_DIR}/mini.exe
    echo "Windows not implemented." > "$STDERR"
    ;;
esac
