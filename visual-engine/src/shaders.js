// Ashima / Stefan Gustavson 3D simplex noise (MIT).
const noise = /* glsl */ `
vec3 mod289(vec3 x){return x-floor(x*(1./289.))*289.;}
vec4 mod289(vec4 x){return x-floor(x*(1./289.))*289.;}
vec4 permute(vec4 x){return mod289(((x*34.)+1.)*x);}
vec4 taylorInvSqrt(vec4 r){return 1.79284291400159-.85373472095314*r;}
float snoise(vec3 v){
  const vec2 C=vec2(1./6.,1./3.);const vec4 D=vec4(0.,.5,1.,2.);
  vec3 i=floor(v+dot(v,C.yyy));vec3 x0=v-i+dot(i,C.xxx);
  vec3 g=step(x0.yzx,x0.xyz);vec3 l=1.-g;vec3 i1=min(g.xyz,l.zxy);vec3 i2=max(g.xyz,l.zxy);
  vec3 x1=x0-i1+C.xxx;vec3 x2=x0-i2+C.yyy;vec3 x3=x0-D.yyy;
  i=mod289(i);
  vec4 p=permute(permute(permute(i.z+vec4(0.,i1.z,i2.z,1.))+i.y+vec4(0.,i1.y,i2.y,1.))+i.x+vec4(0.,i1.x,i2.x,1.));
  float n_=.142857142857;vec3 ns=n_*D.wyz-D.xzx;
  vec4 j=p-49.*floor(p*ns.z*ns.z);vec4 x_=floor(j*ns.z);vec4 y_=floor(j-7.*x_);
  vec4 x=x_*ns.x+ns.yyyy;vec4 y=y_*ns.x+ns.yyyy;vec4 h=1.-abs(x)-abs(y);
  vec4 b0=vec4(x.xy,y.xy);vec4 b1=vec4(x.zw,y.zw);
  vec4 s0=floor(b0)*2.+1.;vec4 s1=floor(b1)*2.+1.;vec4 sh=-step(h,vec4(0.));
  vec4 a0=b0.xzyw+s0.xzyw*sh.xxyy;vec4 a1=b1.xzyw+s1.xzyw*sh.zzww;
  vec3 p0=vec3(a0.xy,h.x);vec3 p1=vec3(a0.zw,h.y);vec3 p2=vec3(a1.xy,h.z);vec3 p3=vec3(a1.zw,h.w);
  vec4 norm=taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));
  p0*=norm.x;p1*=norm.y;p2*=norm.z;p3*=norm.w;
  vec4 m=max(.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.);m=m*m;
  return 42.*dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));
}
vec3 snoise3(vec3 p){return vec3(snoise(p),snoise(p+vec3(17.1,3.7,-9.2)),snoise(p+vec3(-31.7,23.3,5.1)));}
`

export const vertexShader = /* glsl */ `
uniform float uTime, uFlow, uPixelRatio, uSize;
uniform float uIdle, uExplore, uFocus, uConflict, uInsight, uCollapse, uDelta;
uniform float uCollapseAngle, uUncertainty, uTintAmt;
uniform vec3 uTint;
attribute vec2 aUV;
attribute vec4 aSeed;
varying vec3 vColor;
varying float vAlpha;
${noise}
const float TAU = 6.2831853;

vec2 rot(vec2 p, float a){ float c=cos(a), s=sin(a); return vec2(c*p.x-s*p.y, s*p.x+c*p.y); }
float angDist(float a, float b){ return abs(mod(a-b+3.14159265, TAU)-3.14159265); }

void main(){
  float u = aUV.x * TAU;
  float v = aUV.y * TAU;
  float f = uFlow;
  float D = uDelta;

  // Δ: the band carries two latent strands (the two halves of its cross-section).
  // At Δ=0 they form one body; as Δ rises they twist at different rates and pull apart.
  float strand = aUV.y < 0.5 ? -1.0 : 1.0;

  // insight: cross-section snaps onto discrete helical ribbons (crystallisation)
  float bands = 22.0;
  float vq = (floor(aUV.y*bands)+0.5)/bands*TAU;
  v = mix(v, vq, uInsight*0.92);

  // ---- hidden topology: a twisted elliptical torus with a saddle fold ----
  float twist = 1.5*u + 0.35*sin(f*0.3) + strand*D*0.9*sin(2.0*u + f*0.4);
  float R  = 1.18 + 0.16*sin(3.0*u + f*0.4) - 0.12*uCollapse - 0.1*uFocus;
  float ra = 0.62*(1.0 + 0.28*sin(2.0*u - f*0.5)) * (1.0 + 0.2*uExplore);
  float rb = 0.17 + 0.08*cos(3.0*u + f*0.35) + 0.04*uExplore;
  // volumetric interior: a quarter of the points fill the body
  float fill = aSeed.y < 0.25 ? sqrt(aSeed.y/0.25) : 1.0;
  vec2 cs = rot(vec2(cos(v)*ra, sin(v)*rb)*fill, twist);
  vec3 e1 = vec3(cos(u), 0.0, sin(u));
  vec3 C  = vec3(R*cos(u), 0.38*sin(2.0*u + 0.3*sin(f*0.2)), R*sin(u));
  // Δ: the spine itself buckles into a more complex, less symmetric loop
  C += snoise3(vec3(cos(u), sin(u), 0.0)*1.3 + vec3(0.0, 0.0, f*0.08)) * D * 0.35;
  // strands separate along the band's minor axis
  cs += rot(vec2(0.0, strand), twist) * D * 0.32 * (0.75 + 0.25*sin(3.0*u - f*0.5));
  vec3 pos = C + e1*cs.x + vec3(0.0,1.0,0.0)*cs.y;
  vec3 n = normalize(pos - C + 1e-4);

  // uncertainty -> diffuse shell thickness
  float thick = 0.03 + 0.12*uUncertainty + 0.04*uExplore + 0.05*D + 0.06*uConflict - 0.025*uInsight - 0.02*uFocus;
  pos += n * (aSeed.x - 0.5) * thick;

  // ---- noise field (turbulence) ----
  float amp  = 0.05 + 0.08*uUncertainty + 0.07*uExplore + 0.05*D + 0.06*uConflict - 0.04*uInsight - 0.03*uFocus;
  float freq = 0.9 + 0.5*D + 0.3*uExplore;
  vec3 q = pos*freq + vec3(0.0, f*0.25, f*0.1) + strand*D*1.5;
  vec3 turb = snoise3(q);
  pos += turb * max(amp, 0.0);


  // ---- exploration: tendrils reaching into idea-space ----
  float nB = 3.0 + floor(D*3.0);
  float mask = smoothstep(0.72, 1.0, 0.5+0.5*sin(nB*u + 0.6*sin(v) + f*0.35));
  float isTendril = step(aSeed.z, 0.2 + 0.15*D);
  float reach = pow(aSeed.x, 1.4) * (1.6 + 0.5*D) * mask * isTendril * uExplore;
  // every point at the same spine position shares one direction -> coherent filaments
  vec3 tdir = normalize(e1*0.7 + 0.8*snoise3(C*0.7 + vec3(f*0.1)));
  pos = mix(pos, C, clamp(reach*0.6, 0.0, 0.85)) + tdir * reach;

  // ---- concentration: compute pulled toward a focal core, swirling ----
  vec3 focal = vec3(0.0, 0.08*sin(f*0.7), 0.0);
  float pull = uFocus * (0.55 + 0.3*aSeed.z);
  pos = mix(pos, focal + (pos-focal)*0.42, pull);
  pos.xz = rot(pos.xz, uFocus * (1.2 - length(pos)) * 1.4);

  // ---- conflict: two poles counter-rotating, a seam of tension between them ----
  float side = smoothstep(-0.35, 0.35, cos(u + 0.4*sin(f*0.3)));
  float pole = side*2.0 - 1.0;
  float seam = 1.0 - abs(pole);
  vec3 pc = vec3(pole*0.75, 0.0, 0.0) * uConflict;
  vec3 lp = pos - pc*0.5;
  lp.xz = rot(lp.xz, pole * uConflict * (0.5 + 0.45*sin(f*0.6)));
  lp.xy = rot(lp.xy, pole * uConflict * 0.35);
  pos = mix(pos, lp + pc, uConflict);
  pos += turb * seam * uConflict * 0.28;

  // ---- collapse: one region loses its hypothesis and dissolves ----
  float cm = smoothstep(0.85, 0.1, angDist(u, uCollapseAngle));
  float drift = uCollapse * cm * (0.3 + aSeed.x);
  pos += (n*0.9 + turb*1.4 + vec3(0.0,-0.5,0.0)) * drift;

  // ---- halo dust: sparse ambient field around the body ----
  float halo = step(0.955, aSeed.y);
  vec3 hp = normalize(vec3(aSeed.z-0.5, aSeed.x-0.5, aSeed.w-0.5) + 1e-3) * (2.4 + 2.0*aSeed.x);
  hp += snoise3(hp*0.3 + f*0.05) * 0.4;
  hp *= 1.0 + 0.25*uExplore - 0.15*uFocus;
  pos = mix(pos, hp, halo);

  // breathing
  pos *= 1.0 + 0.028*sin(uTime*0.75) * (0.5 + uIdle) + 0.07*uExplore - 0.04*uFocus;

  // ---- colour = cognitive state ----
  vec3 deep   = vec3(0.10, 0.20, 0.75);
  vec3 cyan   = vec3(0.30, 0.80, 1.00);
  vec3 violet = vec3(0.55, 0.32, 1.00);
  vec3 amber  = vec3(1.00, 0.55, 0.18);
  vec3 ember  = vec3(1.00, 0.28, 0.20);
  float t1 = 0.5 + 0.5*sin(v + 1.5*u + turb.x*1.5);
  vec3 col = mix(deep, cyan, t1);
  col = mix(col, violet, clamp(0.25 + 0.5*turb.y + 0.35*D*(strand*0.5+0.5), 0.0, 1.0) * (0.4 + 0.5*uExplore));
  col = mix(col, cyan*1.25, uFocus * (1.0 - length(pos)*0.8));
  vec3 poleCol = mix(cyan, amber, side);
  col = mix(col, poleCol, uConflict*0.55);
  col = mix(col, ember, uConflict * seam * 0.8);
  float crystal = pow(0.5+0.5*cos((aUV.y*bands - floor(aUV.y*bands))*TAU), 6.0);
  col = mix(col, vec3(1.0, 0.97, 0.9), uInsight * (0.35 + 0.5*crystal));
  col = mix(col, mix(cyan, vec3(0.85,0.95,1.0), aSeed.z), clamp(reach, 0.0, 1.0)*0.8);
  col = mix(col, mix(violet, ember, 0.4) * 0.7, cm * uCollapse);
  // live: the cognitive function currently running tints the body
  col = mix(col, uTint, uTintAmt * 0.45 * (1.0 - halo));
  col = mix(col, mix(deep, violet, aSeed.z), halo);

  // alpha
  float a = 0.55 + 0.35*aSeed.z;
  a *= 1.0 - cm*uCollapse*(0.55 + 0.4*aSeed.x);
  a *= mix(1.0, 0.25, halo);
  vAlpha = a * (0.8 + 0.35*uInsight + 0.2*uFocus);
  vColor = col;

  vec4 mv = modelViewMatrix * vec4(pos, 1.0);
  gl_Position = projectionMatrix * mv;
  float sz = uSize * (0.55 + 0.9*aSeed.x*aSeed.z) * (1.0 + 0.6*halo);
  gl_PointSize = sz * uPixelRatio * (4.0 / -mv.z);
}
`

export const fragmentShader = /* glsl */ `
varying vec3 vColor;
varying float vAlpha;
void main(){
  float d = length(gl_PointCoord - 0.5);
  float a = smoothstep(0.5, 0.0, d);
  a *= a;
  gl_FragColor = vec4(vColor, a * vAlpha);
}
`
