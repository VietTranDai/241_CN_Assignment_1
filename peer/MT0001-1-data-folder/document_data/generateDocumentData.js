const fs = require('fs');
const path = require('path');

// Đường dẫn tới folder chứa file
const folderPath =
  'C:\\Users\\Viet\\OneDrive\\Desktop\\CNPM_Project\\backend\\prisma\\data\\document_data';

// Function chuyển file sang Base64
function convertFileToBase64(filePath) {
  const fileContent = fs.readFileSync(filePath);
  return fileContent.toString('base64');
}

// Function đọc file trong folder và tạo dữ liệu document
function generateDocumentData(folderPath) {
  const files = fs.readdirSync(folderPath); // Lấy danh sách file trong folder
  const documentData = files.map((file, index) => {
    const filePath = path.join(folderPath, file);
    const fileName = path.basename(file); // Lấy tên file
    const fileType = path.extname(file).replace('.', ''); // Lấy phần mở rộng file (e.g., pdf, jpg)
    const fileContent = convertFileToBase64(filePath); // Chuyển nội dung file sang Base64

    // Tạo dữ liệu cho mỗi document
    return {
      customerId: '3e021fb4-0709-4a78-b95c-f218b6e1edd0', // ID khách hàng cố định
      fileName: fileName,
      fileType: fileType,
      totalCostPage: Math.floor(Math.random() * 20) + 1, // Random số trang (1-20)
      printSideType: index % 2 === 0 ? 'SINGLE_SIDE' : 'DOUBLE_SIDE', // Xen kẽ kiểu in
      pageSize: index % 3 === 0 ? 'A3' : 'A4', // Xen kẽ A3 và A4
      pageToPrint: JSON.stringify([1, 2, 3, 4, 5]), // Ví dụ trang cần in
      numOfCop: Math.floor(Math.random() * 5) + 1, // Random số bản sao (1-5)
      documentStatus: ['PENDING', 'IS_PRINTING', 'COMPLETED', 'FAILED'][
        index % 4
      ], // Xen kẽ trạng thái
      fileContent: fileContent, // Nội dung Base64
    };
  });

  return documentData;
}

// Tạo dữ liệu và export
const documentData = generateDocumentData(folderPath);

// Tạo file xuất dữ liệu
const outputFilePath = path.join(folderPath, 'documentData.js');
const outputContent = `export const documentData = ${JSON.stringify(documentData, null, 2)};`;

// Ghi dữ liệu vào file
fs.writeFileSync(outputFilePath, outputContent);

console.log(`Document data generated and saved to ${outputFilePath}`);
