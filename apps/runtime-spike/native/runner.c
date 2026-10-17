#define _GNU_SOURCE
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/types.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

/* This is process ownership, not a sandbox. Every child has the app's UID. */
static volatile sig_atomic_t stopped;
static void stop(int sig) { stopped = sig; }
static double now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec / 1e9;
}
int main(int argc, char **argv) {
    if (argc == 2 && !strcmp(argv[1], "--probe")) {
        struct utsname u;
        uname(&u);
        printf("uid=%d pid=%d machine=%s page_size=%ld\n", getuid(), getpid(),
               u.machine, sysconf(_SC_PAGESIZE));
        return 0;
    }
    if (argc < 3) { fprintf(stderr, "usage: runner seconds executable [args]\n"); return 2; }
    int seconds = atoi(argv[1]);
    if (seconds < 1 || seconds > 180) return 2;
    struct sigaction sa = {.sa_handler = stop};
    sigemptyset(&sa.sa_mask);
    sigaction(SIGTERM, &sa, NULL);
    sigaction(SIGINT, &sa, NULL);
    pid_t owner = getppid();
    prctl(PR_SET_PDEATHSIG, SIGTERM);
    if (getppid() != owner) return 125;
    pid_t child = fork();
    if (child < 0) return 125;
    if (!child) {
        /* Only this owned group is signalled by the supervisor. */
        if (setsid() < 0) _exit(125);
        signal(SIGTERM, SIG_DFL);
        signal(SIGINT, SIG_DFL);
        prctl(PR_SET_PDEATHSIG, SIGKILL);
        if (getppid() == 1) _exit(125);
        execv(argv[2], &argv[2]);
        fprintf(stderr, "execv %s: %s\n", argv[2], strerror(errno));
        _exit(126);
    }
    double deadline = now() + seconds;
    siginfo_t info;
    memset(&info, 0, sizeof(info));
    while (!stopped && now() < deadline) {
        /* Keep the group leader unreaped until cleanup, preventing PID reuse. */
        if (waitid(P_PID, child, &info, WEXITED | WNOHANG | WNOWAIT) < 0 && errno != EINTR)
            break;
        if (info.si_pid) break;
        usleep(20000);
    }
    int timed_out = !info.si_pid && !stopped;
    kill(-child, SIGTERM);
    usleep(150000);
    kill(-child, SIGKILL);
    kill(child, SIGKILL); /* Covers cancellation before the child establishes its group. */
    int status;
    while (waitpid(child, &status, 0) < 0) { if (errno != EINTR) return 125; }
    if (stopped) return 130;
    if (timed_out) return 124;
    if (WIFEXITED(status)) return WEXITSTATUS(status);
    return 128 + WTERMSIG(status);
}
