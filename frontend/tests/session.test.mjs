import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import ts from "typescript";
async function setup(cookieMode=false) {
 process.env.NEXT_PUBLIC_SESSION_TRANSPORT=cookieMode === "native" ? "native" : cookieMode ? "cookie" : "bearer";
 const store=new Map(); const events=new EventTarget();
 globalThis.window=Object.assign(events,{localStorage:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v),removeItem:k=>store.delete(k)}});
 const source=readFileSync(new URL("../src/lib/api.ts",import.meta.url),"utf8").replace('import("./native-token-vault")','Promise.resolve({createNativeTokenVault: async () => globalThis.__testVault})');
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

test("cookie session refresh is shared without readable bearer tokens",async()=>{
 const {api,setTokens,getToken}=await setup(true);setTokens("unused","unused");
 assert.equal(getToken(),null);let refreshes=0;let renewed=false;
 globalThis.fetch=async(url,options)=>{
   assert.equal(options.credentials,"include");
   if(url.endsWith("/browser/refresh")) {
     refreshes++;await new Promise(r=>setTimeout(r,20));renewed=true;return json({detail:"ok"});
   }
   assert.equal(options.headers.get("Authorization"),null);
   return renewed?json({ok:true}):json({},401);
 };
 const results=await Promise.all([api.get("/a"),api.get("/b")]);
 assert.ok(results.every(x=>x.ok));assert.equal(refreshes,1);
 assert.equal(window.localStorage.getItem("am_access_token"),null);
});

async function vaultClass() {
 const source=readFileSync(new URL("../src/lib/token-vault.ts",import.meta.url),"utf8");
 const code=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText;
 return (await import("data:text/javascript;base64,"+Buffer.from(code).toString("base64"))).TokenVault;
}
test("native vault restores one secure pair and rejects partial data",async()=>{
 const Vault=await vaultClass();let value={access:"a",refresh:"r"};
 const store={read:async()=>value,write:async v=>{value=v},remove:async()=>{value=null}};
 const vault=new Vault(store);await vault.initialize();assert.equal(vault.access,"a");
 value={access:"partial"};const corrupt=new Vault(store);await corrupt.initialize();
 assert.equal(corrupt.access,null);assert.equal(value,null);
});
test("native vault never exposes tokens after a failed secure write",async()=>{
 const Vault=await vaultClass();const vault=new Vault({read:async()=>null,write:async()=>{throw Error("locked")},remove:async()=>{}});
 await vault.initialize();await assert.rejects(vault.save({access:"a",refresh:"r"}));
 assert.equal(vault.access,null);assert.equal(vault.refresh,null);
});
test("native logout follows pending save and prevents token restoration",async()=>{
 const Vault=await vaultClass();let release;let started;const ready=new Promise(r=>started=r);let value=null;
 const vault=new Vault({read:async()=>null,write:async tokens=>{started();await new Promise(r=>release=r);value=tokens},remove:async()=>{value=null}});
 const saving=vault.save({access:"a",refresh:"r"});await ready;
 const clearing=vault.clear();release();await Promise.all([saving,clearing]);
 assert.equal(vault.access,null);assert.equal(value,null);
});
test("native vault propagates secure deletion failures",async()=>{
 const Vault=await vaultClass();const vault=new Vault({read:async()=>({access:"a",refresh:"r"}),write:async()=>{},remove:async()=>{throw Error("locked")}});
 await vault.initialize();await assert.rejects(vault.clear());assert.equal(vault.access,null);
});

test("native API refresh persists securely without localStorage tokens",async()=>{
 const Vault=await vaultClass();let stored=null;
 const vault=new Vault({read:async()=>stored,write:async v=>{stored=v},remove:async()=>{stored=null}});
 globalThis.__testVault=vault;
 const {api,setTokens,clearTokens,getToken}=await setup("native");
 await setTokens("old","r1");
 globalThis.fetch=async(url,options)=>{
   if(url.endsWith("/auth/refresh"))return json({access_token:"new",refresh_token:"r2"});
   return options.headers.get("Authorization")==="Bearer new"?json({ok:true}):json({},401);
 };
 assert.equal((await api.get("/a")).ok,true);
 assert.deepEqual(stored,{access:"new",refresh:"r2"});
 assert.equal(window.localStorage.getItem("am_access_token"),null);
 assert.equal(window.localStorage.getItem("am_refresh_token"),null);
 await clearTokens();assert.equal(stored,null);assert.equal(getToken(),null);
 delete globalThis.__testVault;
});


test("validation responses display messages without serializing sensitive input", async () => {
 const {api}=await setup();
 globalThis.fetch=async()=>json({detail:[{msg:"Value error, Data nașterii nu poate fi în viitor.",
   input:"private-input-marker",ctx:{error:"private-context-marker"}},null,{input:"private"}]},422);
 await assert.rejects(api.put("/patients/me",{}),error=>{
   assert.equal(error.status,422);
   assert.equal(error.message,"Data nașterii nu poate fi în viitor.");
   assert.ok(!error.message.includes("private"));return true;
 });
});
