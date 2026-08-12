import * as auth from './auth';
import * as projects from './projects';
import * as assets from './assets';
import * as jobs from './jobs';
import * as reports from './reports';
import * as audit from './audit';

export const api = { ...auth, ...projects, ...assets, ...jobs, ...reports, ...audit };
export * from './types';
