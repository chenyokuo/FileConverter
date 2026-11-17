import assert from 'node:assert/strict';
import {importedClips,patchClip,splitClips,related} from '../src/editor-model.ts';
const asset={path:'source.mp4',name:'source',kind:'video',duration:2,hasAudio:true};
let clips=importedClips(asset,'V1',0);
assert.equal(clips.length,2);assert.equal(clips[0].videoOnly,true);assert.equal(clips[1].track,'A1');
clips=patchClip(clips,clips[0],{at:1,in:.2,out:1.8});
assert.equal(clips[1].at,1);assert.equal(clips[1].in,.2);
clips=splitClips(clips,clips[0],1.8);assert.equal(clips.length,4);
assert.equal(clips.filter(c=>c.track==='A1').length,2);
const left=clips[0];assert.equal(clips.filter(c=>related(left,c)).length,2);
const unlinked=clips.map(c=>({...c,linked:false}));
assert.equal(patchClip(unlinked,unlinked[0],{at:3})[1].at,unlinked[1].at);
assert.equal(importedClips({...asset,hasAudio:false},'V1',0).length,1);
assert.equal(importedClips({...asset,kind:'audio'},'A2',0).length,1);
console.log('PASS linked import, move/trim, split, unlink, silent video and audio-only source');

assert.equal(importedClips(asset,'V2',0,importedClips(asset,'V1',0))[1].track,'A2');
