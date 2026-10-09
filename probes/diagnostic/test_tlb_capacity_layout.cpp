// SPDX-License-Identifier: Apache-2.0
// 守住冻结矩阵、旧九页前缀和真实竞争链的契约；不推断设备 PMU 行为。
// 设计锚点：docs/design/2026-10-09-tlb-local-capacity.md。
#include <cstdio>
#if __has_include("tlb_capacity_layout.h")
#include "tlb_capacity_layout.h"
#include <cassert>
#include <set>
#include <tuple>
#include <unistd.h>
#if __has_include("tlb_capacity.cpp")
// 直接调用生产 CLI，避免测试另写一份 --plan 生成器。
#define main tlb_capacity_cli_main
#include "tlb_capacity.cpp"
#undef main
#define CAPACITY_CLI_PRESENT 1
#else
#define CAPACITY_CLI_PRESENT 0
#endif

// 真实内存逐次读取，防止仅检查写入的 next 值却漏掉闭环/方向错误。
static void competitor_rings() {
    alignas(4096) char memory[12*4096]{};
    tlb_local::Addresses pages;
    for(unsigned i=0;i<12;++i) pages.push_back(reinterpret_cast<uintptr_t>(memory)+4096*i);
    for(unsigned k=0;k<=11;++k) for(unsigned direction=0;direction<2;++direction) {
        tlb_capacity::link(pages,1,k,direction);
        auto p=tlb_capacity::competitor_start(pages,k,direction),start=p;
        assert(p==(k?tlb_history::node(pages,direction?k:1):0));
        for(unsigned i=0;i<k;++i) {
            unsigned index=direction?k-i:i+1;
            assert(p==tlb_history::node(pages,index));
            assert((p&4095)==64*index);
            p=tlb_capacity::walk_competitors(p,1);
        }
        assert(p==start);
        auto before=std::vector<char>(memory,memory+sizeof(memory));
        assert(tlb_capacity::walk_competitors(start,k)==start);
        assert(std::equal(before.begin(),before.end(),memory));
        // victim slot0 自环；竞争链不得改写它，且试探恰好一次读取。
        auto victim=tlb_history::node(pages,0);
        assert(tlb_history::walk(victim,1,0)==victim);
        for(unsigned i=0;i<12;++i) {
            auto n=tlb_history::node(pages,i);
            assert(tlb_history::walk(n,1,3)==tlb_history::node(pages,(i+1)%12));
            if(i==0 || i>k) assert(tlb_capacity::walk_competitors(n,1)==n);
        }
    }
    // 无效地址也必须在 K0 零次读取时保持安全；空页表不能被解引用。
    assert(tlb_capacity::walk_competitors(1,0)==1);
    assert(tlb_capacity::competitor_start({},0,0)==0);
    for(unsigned w=6;w<=12;++w) {
        tlb_capacity::link(pages,w,0,0);
        for(unsigned direction=0;direction<2;++direction) {
            auto start=tlb_history::node(pages,direction?w-1:0),p=start;
            for(unsigned i=0;i<w;++i) {
                assert(p==tlb_history::node(pages,direction?w-1-i:i));
                p=tlb_history::walk(p,1,direction);
            }
            assert(p==start);
        }
    }
    unsigned rejected=0;
    for(auto shape: {std::tuple<unsigned,unsigned,unsigned>{0,0,0},{13,0,0},{1,12,0},{1,1,2}}) {
        try { tlb_capacity::link(pages,std::get<0>(shape),std::get<1>(shape),std::get<2>(shape)); }
        catch(const std::runtime_error&) { ++rejected; }
    }
    assert(rejected==4);
}

// 选址直接复用 history 最大集合，W/K 不得重新收集页或更改旧前缀。
static void target_geometry() {
    for(uintptr_t hi: {1ull,123ull,65535ull}) {
        auto base=reinterpret_cast<char*>((hi<<28)+123*4096);
        auto old=tlb_local::targets(base,65536,100);
        auto full=tlb_history::targets(base,65536,100);
        for(unsigned h=0;h<2;++h) {
            assert(full[h].size()==12 && std::equal(old[h].begin(),old[h].end(),full[h].begin()));
            std::set<unsigned> other;
            for(auto va:full[h]) {
                assert(tlb_set_collect::set_index(h+1,va)==100);
                other.insert(tlb_set_collect::set_index(2-h,va));
            }
            assert(other.size()==12);
        }
        auto filler=tlb_local::fillers(base+65536ull*4096,2048,full);
        assert(filler.size()==512);
        for(unsigned h=1;h<=2;++h) for(auto va:filler) for(const auto& family:full)
            for(auto target:family) assert(tlb_set_collect::set_index(h,va)!=tlb_set_collect::set_index(h,target));
    }
}

// 独立枚举每个语义条件及其窗口数，避免生产矩阵自身生成自身期望值。
static void matrix() {
    auto cells=tlb_capacity::cells(false),reverse=tlb_capacity::cells(true);
    assert(cells.size()==94 && reverse.size()==94);
    using Key=std::tuple<unsigned,unsigned,unsigned,unsigned,unsigned,unsigned,int,int>;
    std::set<Key> expected,actual;
    for(unsigned h:{1u,2u}) {
        for(unsigned w=6;w<=12;++w) for(unsigned d:{0u,1u}) expected.emplace(128,h,w,0,d,32,1,0);
        for(unsigned w:{7u,8u,9u,10u}) expected.emplace(512,h,w,0,0,32,1,0);
        for(unsigned w:{8u,12u}) expected.emplace(0,h,w,0,0,16,1,0);
        for(unsigned k=0;k<=11;++k) for(unsigned d:{0u,1u}) expected.emplace(128,h,1,k,d,16,2,0);
    }
    for(int block:{0,1}) for(unsigned f:{0u,128u,512u}) expected.emplace(f,1,0,0,0,16,0,block);
    unsigned windows=0;std::set<std::string> ids;
    for(size_t i=0;i<cells.size();++i) {
        const auto& c=cells[i];const auto& r=reverse[cells.size()-1-i];
        auto key=Key{c.f,c.h,c.w,c.k,c.direction,c.rounds,c.kind,c.block};
        actual.insert(key);assert(ids.insert(c.id()).second);
        assert(c.id()==r.id() && c.rounds==r.rounds && c.victim==r.victim);
        assert(c.history==(c.kind?12u:0u));
        assert(c.victim==(c.kind==2?0:-1));
        windows+=c.rounds;
        for(unsigned round=0;round<c.rounds;++round) assert(round<(c.kind==1 && c.f?32u:16u));
    }
    assert(actual==expected && ids.size()==94 && windows==2080);
    for(size_t i=0;i<3;++i) assert(cells[i].kind==0 && cells[i].block==0);
    for(size_t i=cells.size()-3;i<cells.size();++i) assert(cells[i].kind==0 && cells[i].block==1);
}

#if CAPACITY_CLI_PRESENT
// 捕获真实生产 CLI；测试以独立字段契约读取，不依赖 JSON 空白格式。
static std::string capture_cli(std::vector<std::string> args,int expected) {
    std::vector<char*> argv;for(auto& arg:args) argv.push_back(arg.data());
    auto file=std::tmpfile();assert(file);
    std::fflush(stdout);std::fflush(stderr);
    int saved=dup(STDOUT_FILENO),saved_error=dup(STDERR_FILENO);assert(saved>=0 && saved_error>=0);
    assert(dup2(fileno(file),STDOUT_FILENO)>=0);
    assert(dup2(fileno(file),STDERR_FILENO)>=0);
    int result=tlb_capacity_cli_main(static_cast<int>(argv.size()),argv.data());
    std::fflush(stdout);std::fflush(stderr);
    assert(dup2(saved,STDOUT_FILENO)>=0 && dup2(saved_error,STDERR_FILENO)>=0);
    close(saved);close(saved_error);
    assert(result==expected);std::rewind(file);
    std::string text;char line[4096];while(std::fgets(line,sizeof(line),file)) text+=line;
    std::fclose(file);return text;
}

static unsigned field(const std::string& line,const std::string& name) {
    auto at=line.find("\""+name+"\":");assert(at!=std::string::npos);
    return static_cast<unsigned>(std::stoul(line.substr(at+name.size()+3)));
}

static void production_plan() {
    for(bool reverse:{false,true}) {
        std::vector<std::string> args={"tlb_capacity","--plan"};
        if(reverse) args.push_back("--reverse");
        auto output=capture_cli(args,0);auto end=output.find('\n');assert(end!=std::string::npos);
        auto config=output.substr(0,end);
        assert(field(config,"version")==1 && field(config,"target")==100 && field(config,"seed")==137);
        assert(field(config,"max_w")==12 && field(config,"old_prefix")==9 && field(config,"link_slots")==5);
        assert(field(config,"cells")==94 && field(config,"windows")==2080);
        assert(config.find("\"offset_rotate\":true")!=std::string::npos);
        assert(config.find(std::string("\"reverse\":")+(reverse?"true":"false"))!=std::string::npos);
        auto expected=tlb_capacity::cells(reverse);unsigned count=0,windows=0;
        size_t begin=end+1;
        while(begin<output.size()) {
            end=output.find('\n',begin);assert(end!=std::string::npos);
            auto line=output.substr(begin,end-begin);assert(count<expected.size());
            const auto& c=expected[count];
            assert(line.find("\"type\":\"cell\"")!=std::string::npos);
            assert(line.find("\"cell\":\""+c.id()+"\"")!=std::string::npos);
            assert(field(line,"position")==count && field(line,"kind")==static_cast<unsigned>(c.kind));
            assert(field(line,"h")==c.h && field(line,"w")==c.w && field(line,"f")==c.f);
            assert(field(line,"history")==c.history && field(line,"direction")==c.direction && field(line,"k")==c.k);
            assert(field(line,"rounds")==c.rounds && field(line,"block")==static_cast<unsigned>(c.block));
            assert(line.find("\"victim\":"+std::to_string(c.victim)+",")!=std::string::npos);
            windows+=field(line,"rounds");++count;begin=end+1;
        }
        assert(count==94 && windows==2080);
    }
    auto failed=capture_cli({"tlb_capacity","99"},1);
    assert(failed.find("\"metrics\":{}")!=std::string::npos && failed.find("\"failure\":{")!=std::string::npos);
}
#endif

int main() {
    target_geometry();competitor_rings();matrix();
#if CAPACITY_CLI_PRESENT
    production_plan();
    std::puts("PASS: capacity geometry, real rings, K0 and production 94-cell/2080-window plans");
    return 0;
#else
    std::fputs("FAIL: production capacity CLI is absent\n",stderr);return 1;
#endif
}
#else
int main() { std::fputs("FAIL: production capacity layout is absent\n",stderr);return 1; }
#endif
