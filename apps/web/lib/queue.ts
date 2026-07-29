import type { QueueMessage } from '@handfont/contracts';
import { send } from '@vercel/queue';
import { env } from './env';

export async function publishJob(message: QueueMessage): Promise<{messageId:string}> {
  if (env.queueDriver === 'local') return { messageId: `local:${message.jobId}` };
  const result = await send(env.queueTopic, message);
  return { messageId: result.messageId };
}
