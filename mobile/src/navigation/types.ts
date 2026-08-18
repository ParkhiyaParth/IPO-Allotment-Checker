export type IPOsStackParamList = {
  IPOList: undefined;
  IPODetail: { ipoId: string; companyName: string };
  AllotmentCheck: { ipoId: string; companyName: string };
};

export type PANsStackParamList = {
  PANList: undefined;
  AddEditPAN: { profileId: string } | undefined;
  DeviceSync: undefined;
};

export type AllotmentStackParamList = {
  AllotmentList: undefined;
  AllotmentCheck: { ipoId: string; companyName: string };
  FamilyPortfolio: undefined;
};
