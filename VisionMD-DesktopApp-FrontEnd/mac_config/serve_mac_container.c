#include <unistd.h>
#include <libgen.h>
#include <limits.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <mach-o/dyld.h>

int main(int argc, char** argv) {
  char exe[PATH_MAX]; uint32_t sz = sizeof(exe);
  if (_NSGetExecutablePath(exe, &sz) != 0) { perror("_NSGetExecutablePath"); return 1; }

  char resolved[PATH_MAX];
  if (!realpath(exe, resolved)) { perror("realpath"); return 1; }

  char dirbuf[PATH_MAX]; strncpy(dirbuf, resolved, sizeof(dirbuf)); dirbuf[sizeof(dirbuf)-1] = '\0';
  char *d = dirname(dirbuf);                    // <-- use the RETURN VALUE of dirname()
  char target[PATH_MAX]; snprintf(target, sizeof(target), "%s/%s", d, "serve_mac");

  // Build new argv so argv[0] identifies the target process
  char **newargv = (char**)malloc((argc + 1) * sizeof(char*));
  if (!newargv) { perror("malloc"); return 1; }
  newargv[0] = target;
  for (int i = 1; i < argc; ++i) newargv[i] = argv[i];
  newargv[argc] = NULL;

  execv(target, newargv);                       // replace shim with PyInstaller exe
  perror("execv serve_mac");                    // only runs if execv fails
  return 127;
}
