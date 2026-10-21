// CameraBridge's own bounded stdin/stdout adapter for Sony Camera Remote SDK.
// Vendor headers and binaries are supplied separately. No camera secrets in argv.
#include <atomic>
#include <chrono>
#include <cstring>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#include "CameraRemote_SDK.h"
#include "IDeviceCallback.h"
using namespace SCRSDK;
using namespace std::chrono_literals;
struct Callback : IDeviceCallback {
    std::atomic<bool> connected{false};
    std::atomic<unsigned> error{0};
    void OnConnected(DeviceConnectionVersioin) override { connected=true; }
    void OnDisconnected(CrInt32u) override { connected=false; }
    void OnError(CrInt32u e) override { error=e; }
};
static std::map<std::string, CrInt32u> codes = {
    {"iris",CrDeviceProperty_FNumber},{"iris_auto",CrDeviceProperty_IrisModeSetting},
    {"focus_auto",CrDeviceProperty_FocusModeSetting},{"wb_mode",CrDeviceProperty_WhiteBalanceModeSetting},
    {"red_gain",CrDeviceProperty_WhiteBalanceRGain},{"blue_gain",CrDeviceProperty_WhiteBalanceBGain},
    {"gain",CrDeviceProperty_GaindBValue},{"shutter",CrDeviceProperty_ShutterSpeedValue},
    {"colour_temperature",CrDeviceProperty_WhiteBalancePresetColorTemperature},
    {"zoom",CrDeviceProperty_Zoom_Scale},{"zoom_jog",CrDeviceProperty_Zoom_Operation},
    {"focus_jog",CrDeviceProperty_Focus_Operation},
    {"tally_red",CrDeviceProperty_TallyLampControlRed},{"tally_green",CrDeviceProperty_TallyLampControlGreen}
};
static void check(CrError e) { if(e) throw std::runtime_error("SDK error "+std::to_string(e)); }
static std::string hex(const std::string& s) { std::string o;for(unsigned char c:s){o+="0123456789abcdef"[c>>4];o+="0123456789abcdef"[c&15];}return o; }
static std::string unhex(const std::string& s) { if(s=="-")return "";if(s.size()%2||s.size()>8192)throw std::runtime_error("Invalid field");std::string o;for(size_t n=0;n<s.size();n+=2){if(s.find_first_not_of("0123456789abcdefABCDEF",n)<n+2)throw std::runtime_error("Invalid hex");o+=char(std::stoul(s.substr(n,2),nullptr,16));}return o; }
static ICrCameraObjectInfo* camera(const std::string& host) {
    std::istringstream in(host); unsigned ip=0;std::string s;
    for(unsigned n=0;n<4;n++){if(!std::getline(in,s,'.')||s.empty()||s.find_first_not_of("0123456789")!=std::string::npos)throw std::runtime_error("IPv4 address required");auto v=std::stoul(s);if(v>255)throw std::runtime_error("Invalid IPv4");ip|=v<<(8*n);}
    if(std::getline(in,s,'.'))throw std::runtime_error("Invalid IPv4");
    CrInt8u mac[6]={};ICrCameraObjectInfo* info=nullptr;
    check(CreateCameraObjectInfoEthernetConnection(&info,CrCameraDeviceModel_PXW_Z200,ip,mac,CrSSHsupport_ON));
    if(!info)throw std::runtime_error("No camera object");return info;
}
static long long scalar(CrInt64u raw,unsigned type) {
    switch(type&0x1fff){case CrDataType_Int8:return (signed char)raw;case CrDataType_Int16:return (short)raw;case CrDataType_Int32:return (int)raw;default:return (long long)raw;}
}
static std::vector<long long> values(CrDeviceProperty& p) {
    std::vector<long long> out;unsigned t=p.GetValueType(),base=t&0xfff;
    unsigned width=base==1?1:base==2?2:base==3?4:base==4?8:0;
    auto size=p.GetSetValueSize();auto data=p.GetSetValues();
    if(!width||!data||size>65536||size%width)return out;
    for(unsigned i=0;i<size;i+=width){CrInt64u v=0;std::memcpy(&v,data+i,width);out.push_back(scalar(v,t));}
    return out;
}
static bool valid(CrDeviceProperty& p,long long v) {
    auto vs=values(p);if(vs.empty())return false;
    if(p.GetValueType()&CrDataType_RangeBit)return vs.size()==3&&vs[2]>0&&v>=vs[0]&&v<=vs[1]&&(v-vs[0])%vs[2]==0;
    for(auto x:vs)if(x==v)return true;return false;
}
int main() {
    if(!Init()){std::cout<<"{\"error\":\"SDK initialization failed\"}"<<std::endl;return 1;}
    Callback cb;CrDeviceHandle handle=0;
    std::string line;
    while(std::getline(std::cin,line)) {
        if(line.size()>16384)break;
        try {
            std::istringstream in(line);std::string op;in>>op;
            if(op=="quit")break;
            if(op=="version"){std::cout<<"{\"adapter\":1,\"sdk\":\"2.02.00\"}"<<std::endl;continue;}
            if(op=="fingerprint"||op=="connect") {
                if(handle)throw std::runtime_error("Already connected");
                std::string host,u,p,f;in>>host;auto info=camera(host);
                char fp[256]={};CrInt32u count=0;auto err=GetFingerprint(info,fp,&count);
                if(err){info->Release();check(err);}
                if(count>sizeof(fp)){info->Release();throw std::runtime_error("Oversized fingerprint");}
                std::string fingerprint(fp,count);while(!fingerprint.empty()&&fingerprint.back()==0)fingerprint.pop_back();
                if(op=="fingerprint"){info->Release();std::cout<<"{\"fingerprint_hex\":\""<<hex(fingerprint)<<"\"}"<<std::endl;continue;}
                in>>u>>p>>f;u=unhex(u);p=unhex(p);f=unhex(f);
                if(f.empty()||f!=fingerprint){info->Release();throw std::runtime_error("SSH fingerprint mismatch");}
                cb.error=0;cb.connected=false;
                err=Connect(info,&cb,&handle,CrSdkControlMode_Remote,CrReconnecting_OFF,u.c_str(),p.c_str(),fp,count);
                info->Release();std::fill(p.begin(),p.end(),0);check(err);
                for(unsigned n=0;n<160&&!cb.connected&&!cb.error;n++)std::this_thread::sleep_for(50ms);
                if(!cb.connected)throw std::runtime_error("Camera connection failed or timed out");
                std::cout<<"{\"connected\":true}"<<std::endl;continue;
            }
            if(!handle||!cb.connected)throw std::runtime_error("Camera disconnected");
            CrDeviceProperty* props=nullptr;CrInt32 count=0;check(GetDeviceProperties(handle,&props,&count));
            if(!props||count<0||count>20000){if(props)ReleaseDeviceProperties(handle,props);throw std::runtime_error("Invalid property response");}
            try {
                if(op=="state") {
                    std::ostringstream out;out<<"{\"properties\":{";bool first=true;
                    for(auto& entry:codes)for(int n=0;n<count;n++)if(props[n].GetCode()==entry.second){auto& p=props[n];if(!first)out<<",";first=false;
                        out<<"\""<<entry.first<<"\":{\"value\":"<<scalar(p.GetCurrentValue(),p.GetValueType())<<",\"readable\":"<<(p.IsGetEnableCurrentValue()?"true":"false")<<",\"writable\":"<<(p.IsSetEnableCurrentValue()?"true":"false")<<",\"range\":"<<((p.GetValueType()&CrDataType_RangeBit)?"true":"false")<<",\"values\":[";
                        auto vs=values(p);for(size_t i=0;i<vs.size();i++){if(i)out<<",";out<<vs[i];}out<<"]}";break;}
                    out<<"}}";std::cout<<out.str()<<std::endl;
                } else if(op=="set") {
                    std::string key;long long value;if(!(in>>key>>value)||!codes.count(key))throw std::runtime_error("Invalid property");bool found=false;
                    for(int n=0;n<count;n++)if(props[n].GetCode()==codes.at(key)){auto& p=props[n];if(!p.IsSetEnableCurrentValue()||!valid(p,value))throw std::runtime_error("Value unavailable in current camera mode");CrDeviceProperty request;request.SetCode(p.GetCode());request.SetValueType(p.GetValueType() & ~(CrDataType_ArrayBit|CrDataType_RangeBit));request.SetCurrentValue((CrInt64u)value);check(SetDeviceProperty(handle,&request));found=true;break;}
                    if(!found)throw std::runtime_error("Unsupported camera property");std::cout<<"{\"sent\":true}"<<std::endl;
                } else throw std::runtime_error("Unknown operation");
            } catch(...) {ReleaseDeviceProperties(handle,props);throw;}
            ReleaseDeviceProperties(handle,props);
        } catch(const std::exception& e) {std::string msg=e.what();for(auto& c:msg)if(c=='"'||c=='\\'||c<' ')c=' ';std::cout<<"{\"error\":\""<<msg<<"\"}"<<std::endl;}
    }
    if(handle){Disconnect(handle);std::this_thread::sleep_for(200ms);ReleaseDevice(handle);}
    Release();return 0;
}
