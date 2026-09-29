const fs = require('fs');
const path = require('path');
const solc = require('solc');
const { ethers } = require('ethers');

async function main() {
    console.log('========================================================');
    console.log('ReliefChainAudit - Deploying to MST Testnet');
    console.log('========================================================');

    // 1. Read Solidity source
    const contractPath = path.join(__dirname, 'ReliefChainAudit.sol');
    const source = fs.readFileSync(contractPath, 'utf8');

    // 2. Prepare Solidity standard-json input
    const input = {
        language: 'Solidity',
        sources: {
            'ReliefChainAudit.sol': {
                content: source,
            },
        },
        settings: {
            optimizer: {
                enabled: true,
                runs: 200,
            },
            outputSelection: {
                '*': {
                    '*': ['abi', 'evm.bytecode'],
                },
            },
        },
    };

    console.log('1. Compiling ReliefChainAudit.sol...');
    const compiled = JSON.parse(solc.compile(JSON.stringify(input)));

    if (compiled.errors) {
        let hasErrors = false;
        for (const err of compiled.errors) {
            console.log(err.formattedMessage);
            if (err.severity === 'error') hasErrors = true;
        }
        if (hasErrors) {
            throw new Error('Solidity compilation failed.');
        }
    }

    const contractOutput = compiled.contracts['ReliefChainAudit.sol']['ReliefChainAudit'];
    const abi = contractOutput.abi;
    const bytecode = contractOutput.evm.bytecode.object;
    console.log('✓ Compilation successful!');

    // 3. Connect to MST Testnet
    const rpcUrl = process.env.MST_RPC_URL || 'https://testnetrpc.mstblockchain.com';
    let privateKey = process.env.MST_PRIVATE_KEY;
    if (!privateKey) {
        // Try reading from backend/.env
        const envPath = path.join(__dirname, '..', 'backend', '.env');
        if (fs.existsSync(envPath)) {
            const envContent = fs.readFileSync(envPath, 'utf8');
            const match = envContent.match(/MST_PRIVATE_KEY=([^\r\n]+)/);
            if (match && match[1]) privateKey = match[1].trim();
        }
    }
    if (!privateKey) {
        throw new Error('MST_PRIVATE_KEY environment variable is required to deploy.');
    }

    const provider = new ethers.JsonRpcProvider(rpcUrl);
    const wallet = new ethers.Wallet(privateKey, provider);

    console.log('2. Deployer Address:', wallet.address);
    const balance = await provider.getBalance(wallet.address);
    console.log('   Balance:', ethers.formatEther(balance), 'tMSTC');

    // 4. Deploy Contract
    console.log('3. Broadcasting deployment transaction...');
    const factory = new ethers.ContractFactory(abi, bytecode, wallet);
    const contract = await factory.deploy();

    console.log('   Transaction Hash:', contract.deploymentTransaction().hash);
    console.log('4. Waiting for confirmation on MST Blockchain...');
    await contract.waitForDeployment();

    const deployedAddress = await contract.getAddress();
    console.log('========================================================');
    console.log('🎉 SUCCESS! CONTRACT DEPLOYED!');
    console.log('Contract Address:', deployedAddress);
    console.log('Explorer URL:     https://mstscan.com/address/' + deployedAddress);
    console.log('Tx Explorer URL:  https://mstscan.com/tx/' + contract.deploymentTransaction().hash);
    console.log('========================================================');

    // Save deployed address and ABI to a json file
    const deploymentInfo = {
        contractAddress: deployedAddress,
        transactionHash: contract.deploymentTransaction().hash,
        deployer: wallet.address,
        network: 'MST Testnet',
        rpcUrl: rpcUrl,
        timestamp: new Date().toISOString(),
        abi: abi
    };

    fs.writeFileSync(
        path.join(__dirname, 'deployment_info.json'),
        JSON.stringify(deploymentInfo, null, 2)
    );
    console.log('Saved deployment info to contracts/deployment_info.json');
}

main().catch((err) => {
    console.error('Deployment error:', err);
    process.exit(1);
});
