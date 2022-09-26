
export const matchArray = (a, b) => {
  return a.length === b.length && a.every((v, i) => v === b[i]);
};

export const formatSegmentString = (channels) => {
  var channelName = "";
  for (var i = 0; i < channels.length; i++) {
    switch (channels[i]) {
      case 0:
        channelName += "E0";
        break;
      case 1:
        channelName += "E1";
        break;
      case 1.1:
        channelName += "E1A";
        break;
      case 1.2:
        channelName += "E1B";
        break;
      case 1.3:
        channelName += "E1C";
        break;
      case 2:
        channelName += "E2";
        break;
      case 2.1:
        channelName += "E2A";
        break;
      case 2.2:
        channelName += "E2B";
        break;
      case 2.3:
        channelName += "E2C";
        break;
      case 3:
        channelName += "E3";
        break;
    }

    if (i == 0) {
      channelName += " - ";
    }
  }
  return channelName;
};
