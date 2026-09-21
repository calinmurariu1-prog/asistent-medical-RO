import {spawnSync} from "node:child_process";
const url=process.env.NEXT_PUBLIC_API_URL;
if(!url) throw new Error("Set NEXT_PUBLIC_API_URL before building the mobile bundle");
const result=spawnSync(process.execPath,["node_modules/next/dist/bin/next","build"],{
 stdio:"inherit",env:{...process.env,MOBILE_BUILD:"1"}});
process.exit(result.status??1);
