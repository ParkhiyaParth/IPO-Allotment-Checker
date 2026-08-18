export type IPOsStackParamList = {
  IPOList: undefined;
  IPODetail: { ipoId: string; companyName: string };
  AllotmentCheck: { ipoId: string; companyName: string };
};

export type PANsStackParamList = {
  PANList: undefined;
  AddEditPAN: { profileId: string } | undefined;
};
