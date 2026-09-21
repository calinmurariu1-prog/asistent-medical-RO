import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import ts from "typescript";
async function setup() {
 const store=new Map(); const events=new EventTarget();
 globalThis.window=Object.assign(events,{localStorage:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v),removeItem:k=>store.delete(k)}});
 const source=readFileSync(new URL("../src/lib/api.ts",import.meta.url),"utf8");
 const code=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText;
 return import("data:text/javascript;base64,"+Buffer.from(code+`\n//${Math.random()}`).toString("base64"));
}
const json=(value,status=200)=>new Response(JSON.stringify(value),{status});
test("concurrent unauthorized requests share one refresh and retry",async()=>{
 const {api,setTokens}=await setup();setTokens("old","refresh");let refreshes=0;
 globalThis.fetch=async(url,options)=>{
   if(url.endsWith("/auth/refresh")){refreshes++;await new Promise(r=>setTimeout(r,20));return json({access_token:"new",refresh_token:"r2"});}
   return options.headers.get("Authorization")==="Bearer new"?json({ok:true}):json({},401);
 };
 const values=await Promise.all([api.get("/a"),api.get("/b"),api.get("/c")]);
 assert.equal(refreshes,1);assert.ok(values.every(v=>v.ok));
});
test("rejected retried request never loops",async()=>{
 const {api,setTokens,getToken}=await setup();setTokens("old","refresh");let calls=0;
 globalThis.fetch=async(url)=>{calls++;return url.endsWith("/auth/refresh")?json({access_token:"new",refresh_token:"r2"}):json({},401);};
 await assert.rejects(api.get("/a"));assert.equal(calls,3);assert.equal(getToken(),null);
});
test("late refresh cannot restore a logged out session",async()=>{
 const {api,setTokens,clearTokens,getToken}=await setup();setTokens("old","refresh");let finish;let started;
 const pending=new Promise(r=>started=r);
 globalThis.fetch=async(url)=>{if(url.endsWith("/auth/refresh")){started();return new Promise(r=>finish=r);}return json({},401);};
 const request=api.get("/a");await pending;clearTokens();finish(json({access_token:"new",refresh_token:"r2"}));
 await assert.rejects(request);assert.equal(getToken(),null);
});
test("login error never triggers refresh",async()=>{
 const {api,setTokens}=await setup();setTokens("old","refresh");let calls=0;
 globalThis.fetch=async()=>{calls++;return json({},401);};
 await assert.rejects(api.post("/auth/login",{}));assert.equal(calls,1);
});
