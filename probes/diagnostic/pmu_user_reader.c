/* SPDX-License-Identifier: Apache-2.0
 * Metadata-only capability intake for own perf events. Never executes PMU MRS.
 * docs/design/2026-10-13-pmu-user-metadata.md; no global policy mutation.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "../common/perf_group_read.h"
#include <errno.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#if defined(__linux__) && defined(__aarch64__)
#include <linux/perf_event.h>
#include <sched.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <unistd.h>
#endif
static int failure(const char*s,int e){printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\",\"errno\":%d},\"fds_closed\":true,\"global_policy_mutation\":false,\"counter_register_reads\":0}\n",s,e);return 1;}
static void plan(unsigned flag){printf("{\"probe\":\"pmu-user-metadata\",\"version\":1,\"events\":[17,8,112,113],\"config1\":%u,\"cpu\":7,\"pmu_type\":8,\"metadata_only\":true,\"counter_register_reads\":0,\"global_policy_mutation\":false,\"own_thread_only\":true,\"pinned_group\":true,\"exclude_kernel\":true,\"exclude_hv\":true}\n",flag);}
int main(int argc,char**argv){
 if(argc!=4||(strcmp(argv[1],"--plan")&&strcmp(argv[1],"--run"))||strcmp(argv[2],"--config1")||(strcmp(argv[3],"2")&&strcmp(argv[3],"3")))return failure("usage-user-metadata-config1-2-3",0);
 unsigned flag=(unsigned)atoi(argv[3]);plan(flag);if(!strcmp(argv[1],"--plan"))return 0;
#if !defined(__linux__) || !defined(__aarch64__)
 return failure("requires-linux-aarch64",0);
#else
 const char*stage="affinity";int rc=1,saved_errno=0,policy=-1,fd[4]={-1,-1,-1,-1};struct perf_event_mmap_page*page[4]={MAP_FAILED,MAP_FAILED,MAP_FAILED,MAP_FAILED};uint64_t ids[4]={0};const unsigned ev[4]={17,8,112,113};cpu_set_t cp;CPU_ZERO(&cp);CPU_SET(7,&cp);if(sched_setaffinity(0,sizeof(cp),&cp)||sched_getcpu()!=7)goto done;if(sysconf(_SC_PAGESIZE)!=4096){stage="page-size";goto done;}
 stage="policy-read";FILE*f=fopen("/proc/sys/kernel/perf_user_access","r");if(!f)goto done;int parsed=fscanf(f,"%d",&policy);fclose(f);if(parsed!=1||(policy!=0&&policy!=1))goto done;printf("{\"type\":\"policy\",\"perf_user_access\":%d,\"read_only\":true}\n",policy);
 for(unsigned j=0;j<4;++j){struct perf_event_attr a={0};a.size=sizeof(a);a.type=8;a.config=ev[j];a.config1=flag;a.disabled=j==0;a.pinned=j==0;a.exclude_kernel=1;a.exclude_hv=1;a.read_format=PERF_FORMAT_GROUP|PERF_FORMAT_ID|PERF_FORMAT_TOTAL_TIME_ENABLED|PERF_FORMAT_TOTAL_TIME_RUNNING;stage="perf-open-user-config";fd[j]=(int)syscall(SYS_perf_event_open,&a,0,-1,j?fd[0]:-1,PERF_FLAG_FD_CLOEXEC);if(fd[j]<0)goto done;stage="perf-id";if(ioctl(fd[j],PERF_EVENT_IOC_ID,ids+j))goto done;stage="perf-metadata-map";page[j]=mmap(NULL,4096,PROT_READ,MAP_SHARED,fd[j],0);if(page[j]==MAP_FAILED)goto done;}
 stage="perf-enable";if(ioctl(fd[0],PERF_EVENT_IOC_ENABLE,PERF_IOC_FLAG_GROUP))goto done;printf("{\"type\":\"metadata\",\"cpu\":%d,\"events\":[",sched_getcpu());
 for(unsigned j=0;j<4;++j){struct perf_event_mmap_page*p=page[j];uint32_t first=p->lock;__asm__ volatile("":::"memory");uint32_t index=p->index;unsigned width=p->pmc_width;bool cap=p->cap_user_rdpmc;uint64_t offset=p->offset;__asm__ volatile("":::"memory");uint32_t last=p->lock;printf("%s{\"event\":%u,\"id\":%"PRIu64",\"index\":%u,\"pmc_width\":%u,\"cap_user_rdpmc\":%s,\"offset\":%"PRIu64",\"sequence_before\":%u,\"sequence_after\":%u}",j?",":"",ev[j],ids[j],index,width,cap?"true":"false",offset,first,last);}
 puts("]}");stage="perf-disable";if(ioctl(fd[0],PERF_EVENT_IOC_DISABLE,PERF_IOC_FLAG_GROUP))goto done;uint64_t wire[11];ssize_t bytes=read(fd[0],wire,sizeof(wire));struct pg_sample sample;stage="perf-own-group-read";if(bytes!=(ssize_t)sizeof(wire)||pg_decode(wire,11,ids,4,&sample))goto done;if(sched_getcpu()!=7){stage="cpu-drift";goto done;}rc=0;
 done:saved_errno=errno;for(unsigned j=0;j<4;++j){if(page[j]!=MAP_FAILED)munmap(page[j],4096);if(fd[j]>=0)close(fd[j]);}if(rc)return failure(stage,saved_errno);printf("{\"type\":\"final\",\"fds_closed\":true,\"global_policy_mutation\":false,\"counter_register_reads\":0,\"counter_read_qualified\":false}\n");return 0;
#endif
}
