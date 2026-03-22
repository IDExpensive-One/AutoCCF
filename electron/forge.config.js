module.exports = {
  packagerConfig: {
    asar: true,
    ignore: [
      /\.git/,
      /node_modules\/\.cache/,
    ],
    extraResource: [
      './bridge.py',
      '../APoU',
      '../DoPJ',
      '../AutoCCF',
      '../requirements.txt',
    ],
  },
  makers: [
    { name: '@electron-forge/maker-squirrel', config: {} },
    { name: '@electron-forge/maker-zip', platforms: ['darwin', 'linux'] },
  ],
};
