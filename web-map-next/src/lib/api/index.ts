import * as auth from './auth';
import * as projects from './projects';
import * as assets from './assets';
import * as jobs from './jobs';
import * as reports from './reports';
import * as audit from './audit';
import * as admin from './admin';

export const api = { ...auth, ...projects, ...assets, ...jobs, ...reports, ...audit, ...admin };
export { getToken, setToken, setUnauthorizedHandler } from './client';
export * from './types';
