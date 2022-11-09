
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

export const formatStimulationChannel = (channels) => {
  let formattedChannel = [];

  for (let channel of channels) {
    let channelName = "";
    switch (channel.Electrode.toLowerCase()) {
      case "electrodedef.case":
        channelName = "CAN";
        break;
      case "dlectrodedef.fourelectrodes_1":
        channelName = "E1";
        break;
      case "electrodedef.sensight_1a":
        channelName = "E1A";
        break;
      case "electrodedef.sensight_1b":
        channelName = "E1B";
        break;
      case "electrodedef.sensight_1c":
        channelName = "E1C";
        break;
      case "electrodedef.fourelectrodes_2":
        channelName = "E2";
        break;
      case "electrodedef.sensight_2a":
        channelName = "E2A";
        break;
      case "electrodedef.sensight_2b":
        channelName = "E2B";
        break;
      case "electrodedef.sensight_2c":
        channelName = "E2C";
        break;
      default:
        channelName = channel.Electrode;
        break;
    }

    if (channel.ElectrodeStateResult === "ElectrodeStateDef.Positive") {
      channelName += "+";
    } else {
      channelName += "-";
    }

    formattedChannel.push(channelName);
  }

  for (let sign of ["+", "-"]) {
    for (let contact of ["1", "2"]) {
      if (formattedChannel.includes(`E${contact}A${sign}`) && formattedChannel.includes(`E${contact}B${sign}`) && formattedChannel.includes(`E${contact}C${sign}`)) {
        formattedChannel = formattedChannel.filter((value) => value != `E${contact}A${sign}` && value != `E${contact}B${sign}` && value != `E${contact}C${sign}`)
        formattedChannel.push(`E${contact}${sign}`);
      }
    }
  }

  return formattedChannel;
};
