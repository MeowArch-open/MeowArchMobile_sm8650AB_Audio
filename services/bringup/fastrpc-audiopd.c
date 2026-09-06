// Ask the ADSP to create its "audiopd" static protection domain.
//
// zorn's APM (the AudioReach graph service) lives in that PD, and every APM
// command times out while PRM -- which lives in the ADSP's root PD -- answers
// fine. Nothing on the AP side ever creates the PD: mainline has the ioctl
// (FASTRPC_IOCTL_INIT_CREATE_STATIC, drivers/misc/fastrpc.c
// fastrpc_init_create_static_process) but no userspace that calls it, because on
// Android that is adsprpcd's job.
//
//   gcc -O2 -o fastrpc-audiopd fastrpc-audiopd.c
//   ./fastrpc-audiopd [memlen-in-bytes]        default 0x300000
#include <fcntl.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <errno.h>

struct fastrpc_init_create_static {
	uint32_t namelen;
	uint32_t memlen;
	uint64_t name;
};

#define FASTRPC_IOCTL_INIT_CREATE_STATIC _IOWR('R', 9, struct fastrpc_init_create_static)

int main(int argc, char **argv)
{
	const char *pd = "audiopd";
	unsigned long memlen = argc > 1 ? strtoul(argv[1], NULL, 0) : 0x300000;
	struct fastrpc_init_create_static init = {
		.namelen = (uint32_t)strlen(pd) + 1,
		.memlen = (uint32_t)memlen,
		.name = (uint64_t)(uintptr_t)pd,
	};
	int fd = open("/dev/fastrpc-adsp", O_RDWR);

	if (fd < 0) {
		perror("open /dev/fastrpc-adsp");
		return 1;
	}

	printf("creating static PD \"%s\", remote heap %#lx bytes\n", pd, memlen);
	if (ioctl(fd, FASTRPC_IOCTL_INIT_CREATE_STATIC, &init) < 0) {
		printf("INIT_CREATE_STATIC failed: %s (%d)\n", strerror(errno), errno);
		close(fd);
		return 1;
	}

	printf("INIT_CREATE_STATIC ok -- holding the fd open, ^C or SIGTERM to drop the PD\n");
	fflush(stdout);
	pause();          /* the PD lives as long as this fd does */
	close(fd);
	return 0;
}
