from relayer.chainpy.eth.ethtype.amount import EthAmount
from relayer.rbcevents.consts import TokenStreamIndex

USER_CONFIG_PATH = "configs/entity.user.json"
PRIVATE_CONFIG_PATH = "configs/entity.user.private.json"
SCORE_SERVER_URL = "https://leaderboard-api.testnet.thebifrost.io/user/health"

ADMIN_RELAYERS = [
    "0x72da8d1D9Ca516F074E1Bcac413bBC4d12AD7Ca0",
    "0xe838E72EF5183E3977Ec6d6f14F5B78C71c3C0BF",
    "0x694eF94C67A7BE2B268E5C1f08650891Ce25c068",
    "0x9230C674A37B3EeFf5c1c35Da6124aA4CE83aEf2",
    "0x225033E076B0eC3212D763202334136190949f36",
    "0x26590C501c0bAeFB72FFfF51E12b3423e2a5D07f",
    "0xf27CB2b525D9B4c26a84B9A555b6e1917DBea2b7",
    "0x758019aa662c0CE92BE8a9C9b5E18146440e6a11",
    "0x935B00757585A2F0420471Ff70d2bEA452CC7E85",
    "0x98c8F622d81a034059Bdf646f797862E67A7DCf8"
]

ADMIN_CONTROLLER = [
    '0x45A96ACA1Cd759306B05B05b40B082254E77699b',
    '0xf38de36b8a2e9d8eABcE4991b66D9412B843F26a',
    '0xeF3f6F7761d74adadFcEf618608a28E2be330F9D',
    '0x9Cf4C7471fe50B37E06bfccB3b60bD94da7C3422',
    '0x64883c73cc45BF76b215311DF1674F08C90E4868',
    '0x7e8d553150C223f3d121BC06eFE2d3dFAB7B072A',
    '0xB32f77cD600020477DdEaCD65fF2D251eaF3C02B',
    '0x1Aa99316e9622283ef5586306421ad821Dd8AcbC',
    '0xA12c88DeAcad08367538646A7920e6B3846dFDd6',
    '0xFed32aFdE53Db70561ef6F99B488aDb148fc4633'
]

CONTROLLER_TO_DISCORD_ID = {
    "0x5c9EDEf909704b7473DC76876B915Df97c0b3a33": "Orochi \| IONode.Online#4384",
    "0x0cd269016873f3d1F1Dd1B69819982f2dD83e4b8": "!dieuts#4705",
    "0x2BCCdcc63Db052d7f9489ee107C15E3e4FED4f12": "Anton_StakerHouse.com#3624",
    "0x77eE35Eb37F6B67932542b64a8A396D85d893659": "SEM#4095",
    "0x03D80772d8644Fff28495cBc573EE2264629955b": "shurinoff#5643",
    "0x42EE9b2810FC8B8257151182c6d1D487D182f0Fd": "openbitlab#9650",
    "0x4CAd798bdeAabD117687E28C4b868769C81ecA62": "ulad_proto#1044",
    "0xFEf36e78B3Cf81682D4563788c2C1Fa1D01e2616": "whisperit#8145",
    "0xc9975aA3189e4056AeD57B66bBAa8eE5B94D218d": "n1trog3n#5776 | stasrover1331#6263",
    "0xC2548bB2967e9E2DC2726dfCFcb09C8103ec2073": "icodragon [NODERS]#4560",
    "0x5D84b32232c0168921FccED61419C936BB368CbD": "SeptimA [NODERS]#9554",
    "0x791623e0C9BC538311Ad52dD473837d2bFA2Cc52": "kjnodes#8455",
    "0x09E291D0F90773f6dEB88B971B6678b18914C272": "rufernobolsa#0579",
    "0x72aA368Fd5c69EE0010Da7B3419288339973aAb1": "Louis \| ERN VENTURES#5239",
    "0xf0117448D5b1952b494F608ed88B0fbfcB1CebEa": "AlexeyM#5409",
    "0x49B4DC2c156E8C1f41c48AbcfA9D55529e492922": "5ElementsNodes#8384",
    "0xD6D07683964409f2c300A7A88Fb1e7878050e5CC": "Skynode \| Let's Node#5805",
    "0xbbcAAcdAF238D82615A5f3a3bB704a7C61AA47Ab": "Kir \| Genesis Lab#1305",
    "0xBb71C229ACB5EB2306BA00E95244BE6762B43671": "SerGo#8747",
    "0x27Ce111D9488470dEECe38ad601544F2Cc51CBFD": "romanv1812#6131",
    "0x5880ac74B7604573658e506D4d150fffa47fE35d": "rewse#4063",
    "0x70C73Ca8010fb4074A598DDADf90F23c69340379": "sr20de#7650",
    "0xA7f0C4CDcD567708392BAaD6c5675611A4B32325": "Serhio911#2565",
    "0x9c259119F309D2aA8dcBa838D9A4EC77d8d0E8B0": "Jun \| Wetez#9950",
    "0xfcD12865282a86124Ac53E9eE9ef5B806C229948": "Alan \| NodeStake.top#2237",
    "0x27300ea55628C6667C7847Aa514552872f20b54d": "Marc",
    "0xca458aDBCC81bAD309E935BF1ce55E1f181ddd60": "Rok#1767",
    "0x775BbFDeB720bC3eE4314DDc2017F14055cE7F7a": "Nodeist#3299",
    "0x2B2AeeBbCF67e778Bb38c0D42F4790f0C2CDe014": "CT_Mike#1529",
    "0xB875832255e68b56D2CC78eEF7C226f2FD9b5C02": "lsh"
}

RELAYER_ONCE = [
    "0x72da8d1d9ca516f074e1bcac413bbc4d12ad7ca0",
    "0x26590c501c0baefb72ffff51e12b3423e2a5d07f",
    "0x935b00757585a2f0420471ff70d2bea452cc7e85",
    "0x758019aa662c0ce92be8a9c9b5e18146440e6a11",
    "0x9230c674a37b3eeff5c1c35da6124aa4ce83aef2",
    "0x98c8f622d81a034059bdf646f797862e67a7dcf8",
    "0x694ef94c67a7be2b268e5c1f08650891ce25c068",
    "0x225033e076b0ec3212d763202334136190949f36",
    "0xe838e72ef5183e3977ec6d6f14f5b78c71c3c0bf",
    "0xf27cb2b525d9b4c26a84b9a555b6e1917dbea2b7",
    "0xd58a5e0904460161fe5fe3deef482cdedb2949b9",
    "0xf099895c49007aedce4e182861cda11e5150a195",
    "0xeafd8c3e7305fe19bf2dd9a5d6fdb4244e51c7cd",
    "0xeab8207171a23fe9aeb387b67024f1f551036de4",
    "0x0c26b351bb2887eb64f5ee78422ab35f6316a9fe",
    "0x3d0d33acfc1b6f4a8bfa08e7f3897a83f06618c1",
    "0xee08f4ec02573d95ee8468ba6c7abc7c97e1edac",
    "0xba0225b629eeb758c07883a063fe0ba4e1fd86b5",
    "0xd7afe52227116a912cc062fc129420145b6c4f79",
    "0x837828b80fae6284d3352c91f966f53feef72ad7",
    "0x68869908a5eb4f7071871b82438aed76b8880029",
    "0x6d9e874853827742bc3d7ac2c634f2b7346ee6a9",
    "0xd6d764a7df6d4f46ee0ff7e025e48eaceaa776f3",
    "0xcf201f88d74b6c2e7c11ee2d9aca49455d3588a1",
    "0x6cdf54e73196b7876126c3c988a23b5cac319a0c",
    "0x451a6a18884ef5c4b71fbe6c73c85cc2a7bd2e2d",
    "0x8d89dd4f141b13ae38013eb7a9399b9c100773ff",
    "0xb6fe2c4f7beba44ea5f654483ca34615a3d0ec53",
    "0x68fe8d40725b35a0b277b15df885af2145aca148",
    "0xcff607cd709c5dbe993cad54f9700d33dc67e0cf",
    "0x53d2acbba7e803e20539784a51a6d4b025cc0bc4",
    "0x41e1f2155687a0fa3016b61099a525815978ddee",
    "0x25b5d82e8fefcd7837d561c308cd512fb2e35991",
    "0xfcd12865282a86124ac53e9ee9ef5b806c229948",
    "0xee83770168d4ee756e74562c17bded88091519d0",
    "0x5883c43b358f06095994d26fd392b1267426b893",
    "0x1aefa8047797ca844d99fcbe56573044fcdc9eb1",
    "0x7b49ebeeeb008af50842e1a68e3781fef670b2ce"
]


BIFNET_LIMIT_AMOUNT = EthAmount(20.1)
EXTERNAL_LIMIT_AMOUNT = EthAmount(2.0)

SUPPORTED_TOKEN_LIST = [
    # native coins
    TokenStreamIndex.BFC_BIFROST,
    TokenStreamIndex.ETH_ETHEREUM,
    TokenStreamIndex.MATIC_POLYGON,
    TokenStreamIndex.BNB_BINANCE,
    TokenStreamIndex.AVAX_AVALANCHE,

    # tokens
    TokenStreamIndex.BIFI_ETHEREUM,
    TokenStreamIndex.USDC_ETHEREUM,
    TokenStreamIndex.USDT_ETHEREUM,
    TokenStreamIndex.BUSD_BINANCE
]

EXECUTABLE_TOKEN_LIST = [
    TokenStreamIndex.BFC_BIFROST
]
