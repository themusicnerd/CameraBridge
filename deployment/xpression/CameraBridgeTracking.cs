// XPression API signatures verified against the installed Ross 11.5 SDK.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using XPression;

public static class CameraBridgeTracking
{
    static int Signed24(byte[] p, int at)
    {
        int v=(p[at]<<16)|(p[at+1]<<8)|p[at+2];
        return (v & 0x800000)!=0 ? v-0x1000000 : v;
    }
    public static double[] Decode(byte[] p, int cameraId)
    {
        if(p.Length!=29 || p[0]!=0xd1 || p[1]!=cameraId) return null;
        int sum=0; foreach(byte b in p) sum+=b;
        if((sum & 255)!=0x40 || p[26]!=0 || p[27]!=0) return null;
        double[] v=new double[8];
        for(int i=0;i<6;i++) v[i]=Signed24(p,2+i*3)/(i<3 ? 32768.0 : 64.0);
        for(int i=6;i<8;i++) { int at=20+(i-6)*3; v[i]=(p[at]<<16)|(p[at+1]<<8)|p[at+2]; }
        if(Math.Abs(v[0])>180 || Math.Abs(v[1])>90 || Math.Abs(v[2])>180) return null;
        return v;
    }
    public static double? LensFov(List<double[]> points, double encoder)
    {
        if(points.Count<2 || encoder<points[0][0] || encoder>points[points.Count-1][0]) return null;
        for(int i=1;i<points.Count;i++)
            if(encoder<=points[i][0]) {
                double[] a=points[i-1], b=points[i];
                return a[1]+(b[1]-a[1])*(encoder-a[0])/(b[0]-a[0]);
            }
        return null;
    }
    public static List<double[]> LoadLens(string path)
    {
        var points=new List<double[]>();
        if(path.Length==0) return points;
        foreach(string raw in File.ReadAllLines(path)) {
            string line=raw.Trim(); if(line.Length==0 || line.StartsWith("#")) continue;
            string[] pair=line.Split(',');
            if(pair.Length!=2) throw new ArgumentException("Lens CSV needs encoder,horizontal_fov_degrees pairs");
            double encoder=double.Parse(pair[0],CultureInfo.InvariantCulture);
            double fov=double.Parse(pair[1],CultureInfo.InvariantCulture);
            if(Double.IsNaN(encoder)||Double.IsInfinity(encoder)||encoder<0||encoder>0xffffff||
               Double.IsNaN(fov)||Double.IsInfinity(fov)||fov<=0||fov>=180)
                throw new ArgumentException("Invalid lens calibration point");
            points.Add(new double[]{encoder,fov});
        }
        points.Sort((a,b)=>a[0].CompareTo(b[0]));
        if(points.Count<2) throw new ArgumentException("Use at least two measured lens points");
        for(int i=1;i<points.Count;i++) if(points[i][0]<=points[i-1][0]) throw new ArgumentException("Duplicate lens encoder");
        return points;
    }
    public static void Run(string source, string bind, int port, int id, string sceneName, string cameraName,
        int framebuffer, int layer, double panSign, double tiltSign, double rollSign,
        double ox, double oy, double oz, string lensCsv, bool checkOnly, int packetLimit)
    {
        IPAddress allowed=IPAddress.Parse(source);
        var lens=LoadLens(lensCsv);
        xpEngine engine=null;
        // CheckOnly receives and validates data without connecting to XPression.
        if(!checkOnly) engine=new xpEngineClass();
        int count=0; DateTime last=DateTime.MinValue, report=DateTime.MinValue;
        bool stale=false;
        using(var udp=new UdpClient(new IPEndPoint(IPAddress.Parse(bind),port))) {
            udp.Client.ReceiveTimeout=250;
            Console.WriteLine(checkOnly ? "Packet check active. XPression is not controlled." : "XPression tracking adapter active. Press Ctrl+C to stop.");
            while(true) {
                byte[] newest=null; IPEndPoint remote=new IPEndPoint(IPAddress.Any,0);
                try {
                    byte[] p=udp.Receive(ref remote);
                    if(remote.Address.Equals(allowed) && Decode(p,id)!=null) newest=p;
                    // Drain queued packets. Apply only the newest valid pose per pass.
                    int drained=0;
                    while(udp.Available>0 && drained++<256) {
                        p=udp.Receive(ref remote);
                        if(remote.Address.Equals(allowed) && Decode(p,id)!=null) newest=p;
                    }
                } catch(SocketException ex) { if(ex.SocketErrorCode!=SocketError.TimedOut) throw; }
                if(newest==null) {
                    if(last!=DateTime.MinValue && (DateTime.UtcNow-last).TotalSeconds>2 && !stale) {
                        Console.WriteLine("Tracking stale. Camera updates stopped.");stale=true;
                    }
                    continue;
                }
                double[] v=Decode(newest,id);last=DateTime.UtcNow;stale=false;
                if(!checkOnly) {
                    xpOutputFrameBuffer output=null; xpScene scene=null; xpBaseObject obj=null;
                    try {
                    if(!engine.GetOutputFrameBuffer(framebuffer,out output) || !output.GetSceneOnLayer(layer,out scene) ||
                       scene.Name!=sceneName || !scene.GetObjectByName(cameraName,out obj))
                        throw new InvalidOperationException("Put the named scene and camera on the selected framebuffer/layer, then restart the adapter.");
                    xpCameraObject camera=obj as xpCameraObject;
                    if(camera==null) throw new InvalidOperationException("The named object is not an XPression camera.");
                    // Keep scene position, CCD, camera mode and active-camera choice under operator control.
                    camera.SetRotXYZ(v[1]*tiltSign+ox,v[0]*panSign+oy,v[2]*rollSign+oz);
                    double? fov=LensFov(lens,v[6]);
                    if(fov.HasValue) { camera.FOVOrientation=FOVOrientation.fovo_Horizontal;camera.FOV=fov.Value; }
                    } finally {
                        if(obj!=null) Marshal.ReleaseComObject(obj);
                        if(scene!=null) Marshal.ReleaseComObject(scene);
                        if(output!=null) Marshal.ReleaseComObject(output);
                    }
                }
                count++;
                if((DateTime.UtcNow-report).TotalSeconds>=1) {
                    Console.WriteLine("Camera {0}: pan {1:F3}, tilt {2:F3}, zoom {3}; {4} accepted updates{5}",
                        id,v[0],v[1],v[6],count,lens.Count==0 ? "; no lens calibration" : "");report=DateTime.UtcNow;
                }
                if(packetLimit>0 && count>=packetLimit) return;
            }
        }
    }
}
