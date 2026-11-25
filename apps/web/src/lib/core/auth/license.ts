import { useLicenseStatus } from '@core/context/user';
import { selfHostEnabled } from '@core/self-host';
import { createMemo } from 'solid-js';

export function useHasPaidAccess() {
  const licenseStatus = useLicenseStatus();
  return createMemo((): boolean => {
    if (selfHostEnabled()) return true;
    const status = licenseStatus();
    return status === 'trialing' || status === 'active';
  });
}
