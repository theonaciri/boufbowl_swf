import {test,expect} from 'bun:test';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../patches/SoundComp.as',import.meta.url),'utf8');
const body=source.split('public static function fallbackMusicURL(url:String) : String')[1].split('\n      }')[0].replace(/var (\w+):(String|Array|int)/g,'var $1');
const fallback=new Function('url','int',body.slice(body.indexOf('{')+1));
const resolve=url=>fallback(url,Math.trunc);
test('missing stadium music keeps phase, number and asset URL prefix',()=>{
 expect(resolve('../assets/sounds/music/mexico_tactique_02.mp3')).toBe('../assets/sounds/music/music_tactic_loop_02.mp3');
 expect(resolve('app:/assets/sounds/music/brakmar_resolution_03.mp3')).toBe('app:/assets/sounds/music/music_resolution_loop_03.mp3');
 expect(resolve('https://example.test/assets/sounds/music/bonta_tactique_01.mp3?v=2')).toBe('https://example.test/assets/sounds/music/music_tactic_loop_01.mp3?v=2');
 expect(resolve('music/st_ballotin_tactique.mp3')).toBe('music/music_tactic_loop_01.mp3');
});
test('default music and nonmusic failures cannot trigger retry loops',()=>{
 for(const url of [null,'music/music_tactic_loop_02.mp3','music/music_resolution_loop_03.mp3','ambient/amb_larzac.mp3','interactions/hit.mp3'])expect(resolve(url)).toBeNull();
});
