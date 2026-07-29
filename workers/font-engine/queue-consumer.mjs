import { PollingQueueClient } from '@vercel/queue';
import { spawn } from 'node:child_process';
const region=process.env.VERCEL_QUEUE_REGION||'icn1';const topic=process.env.VERCEL_QUEUE_TOPIC||'handfont-jobs';const group=process.env.QUEUE_CONSUMER_GROUP||'font-engine-v1';
const {receive}=new PollingQueueClient({region});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function runPython(message){return new Promise((resolve,reject)=>{const child=spawn('python',['-m','worker.main','--message',JSON.stringify(message)],{stdio:'inherit',env:process.env});child.on('exit',code=>code===0?resolve():reject(new Error(`worker exited ${code}`)));child.on('error',reject)})}
while(true){try{const result=await receive(topic,group,async(message)=>{await runPython(message)},{limit:1});if(!result.ok&&result.reason==='empty')await sleep(1500)}catch(error){console.error(error);await sleep(5000)}}
