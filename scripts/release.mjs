// Version/manifests only. Signing remains in the official Tauri CLI/plugin.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8').replace(/^\uFEFF/,''));
const write=(p,v)=>fs.writeFileSync(path.join(root,p),JSON.stringify(v,null,2)+'\n');
export function validateVersion(v){if(!/^\d+\.\d+\.\d+(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/.test(v))throw Error('Use a plain SemVer version such as 1.1.0-rc.3');return v;}
export function manifest({version,installer,portable,installerSignature,portableSignature,notes,date=new Date().toISOString()}){
 validateVersion(version);
 for(const s of [installerSignature,portableSignature])if(!s?.trim())throw Error('Missing actual Tauri signature');
 const url=name=>`https://github.com/chenyokuo/FileConverter/releases/download/v${version}/${encodeURIComponent(name)}`;
 return {version,notes,pub_date:date,platforms:{'windows-x86_64':{signature:installerSignature.trim(),url:url(installer)},'windows-x86_64-nsis':{signature:installerSignature.trim(),url:url(installer)},'windows-x86_64-portable':{signature:portableSignature.trim(),url:url(portable)}}};
}
export function versions(){
 const cargo=fs.readFileSync(path.join(root,'src-tauri/Cargo.toml'),'utf8').match(/^version\s*=\s*"([^"]+)"/m)?.[1];
 const lock=fs.readFileSync(path.join(root,'src-tauri/Cargo.lock'),'utf8').match(/name = "file-converter"\r?\nversion = "([^"]+)"/)?.[1];
 return [read('package.json').version,read('package-lock.json').version,read('package-lock.json').packages[''].version,read('src-tauri/tauri.conf.json').version,cargo,lock];
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const [action,argument,notesFile]=process.argv.slice(2);
 if(action==='version'){
  const version=validateVersion(argument);
  for(const p of ['package.json','package-lock.json','src-tauri/tauri.conf.json']){const data=read(p);data.version=version;if(data.packages?.[''])data.packages[''].version=version;write(p,data);}
  const cargoPath=path.join(root,'src-tauri/Cargo.toml');fs.writeFileSync(cargoPath,fs.readFileSync(cargoPath,'utf8').replace(/^(version\s*=\s*")[^"]+(")/m,`$1${version}$2`));
  const lockPath=path.join(root,'src-tauri/Cargo.lock');fs.writeFileSync(lockPath,fs.readFileSync(lockPath,'utf8').replace(/(name = "file-converter"\r?\nversion = ")[^"]+(")/,`$1${version}$2`));
  console.log(`Version synchronized: ${version}`);
 }else if(action==='check'){
  const v=versions();if(new Set(v).size!==1||v.some(x=>!x))throw Error('Version mismatch: '+JSON.stringify(v));console.log(v[0]);
 }else if(action==='manifest'){
  const version=validateVersion(argument);if(versions().some(v=>v!==version))throw Error('Version mismatch');
  const dir=path.join(root,'release',version);fs.mkdirSync(dir,{recursive:true});
  const installer=`FileConverter_${version}_x64-setup.exe`,portable=`FileConverter-${version}-windows-x64-portable.zip`;
  for(const name of [installer,installer+'.sig',portable,portable+'.sig'])if(!fs.statSync(path.join(dir,name)).size)throw Error('Empty artifact: '+name);
  const notes=fs.readFileSync(notesFile,'utf8').replace(/^\uFEFF/,'');
  write(`release/${version}/latest.json`,manifest({version,installer,portable,notes,installerSignature:fs.readFileSync(path.join(dir,installer+'.sig'),'utf8'),portableSignature:fs.readFileSync(path.join(dir,portable+'.sig'),'utf8')}));
  const sums={};for(const name of [installer,installer+'.sig',portable,portable+'.sig','latest.json']){const hash=crypto.createHash('sha256');for await(const chunk of fs.createReadStream(path.join(dir,name)))hash.update(chunk);sums[name]=hash.digest('hex');}
  write(`release/${version}/SHA256SUMS.json`,sums);fs.writeFileSync(path.join(dir,'SHA256SUMS.txt'),Object.entries(sums).map(([n,h])=>`${h}  ${n}`).join('\n')+'\n');
  console.log('Generated versioned release manifests and SHA-256 checksums.');
 }else throw Error('Use version <version>, check or manifest <version> <notes file>');
}
